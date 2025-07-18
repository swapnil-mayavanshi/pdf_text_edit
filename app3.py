import os
import tempfile
import zipfile
import shutil
from flask import Flask, render_template, request, send_file
import fitz
import pandas as pd

app = Flask(__name__)
UPLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- SET FIXED VALUES HERE ---
FONT_PATH = "times.ttf"
PREFERRED_SIZE = 11
EXPAND = 2.5
Y_SHIFT = 1.5
# -----------------------------

def process_pdf(pdf_path, output_path, search_str, replace_str):
    doc = fitz.open(pdf_path)
    for page in doc:
        text_instances = page.search_for(search_str)
        for rect in text_instances:
            new_rect = fitz.Rect(
                rect.x0 - EXPAND,
                rect.y0 + Y_SHIFT - 1,
                rect.x1 + EXPAND,
                rect.y1 + Y_SHIFT + 1
            )
            page.draw_rect(new_rect, color=(1, 1, 1), fill=(1, 1, 1))
            rc = page.insert_textbox(
                new_rect,
                replace_str,
                fontname="TimesNewRomanPSMT",
                fontfile=FONT_PATH,
                fontsize=PREFERRED_SIZE,
                color=(0, 0, 0),
                align=1,
            )
            if rc < 0:
                rc = page.insert_textbox(
                    new_rect,
                    replace_str,
                    fontname="TimesNewRomanPSMT",
                    fontfile=FONT_PATH,
                    fontsize=PREFERRED_SIZE - 1,
                    color=(0, 0, 0),
                    align=1,
                )
    doc.save(output_path)
    doc.close()
    return output_path

def process_csv(csv_path, output_path, search_str, replace_str):
    df = pd.read_csv(csv_path, dtype=str, encoding='utf-8', engine='python')
    df = df.applymap(lambda x: x.replace(search_str, replace_str) if isinstance(x, str) else x)
    df.to_csv(output_path, index=False, encoding='utf-8')
    return output_path

def process_xpt(xpt_path, output_path, search_str, replace_str):
    df = pd.read_sas(xpt_path, format='xport', encoding='utf-8')
    df = df.applymap(lambda x: x.replace(search_str, replace_str) if isinstance(x, str) else x)
    df.to_xpt(output_path, index=False)
    return output_path

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        search_str = request.form['search_str']
        replace_str = request.form['replace_str']

        temp_dir = tempfile.mkdtemp()
        uploaded_file = request.files['data_file']
        file_ext = os.path.splitext(uploaded_file.filename)[1].lower()
        processed_files = []

        def process_one(data_path, filename):
            ext = os.path.splitext(filename)[1].lower()
            base = os.path.splitext(os.path.basename(filename))[0]
            if ext == '.pdf':
                outpath = os.path.join(temp_dir, f"{base}_replaced.pdf")
                process_pdf(data_path, outpath, search_str, replace_str)
                return outpath
            elif ext == '.csv':
                outpath = os.path.join(temp_dir, f"{base}_replaced.csv")
                process_csv(data_path, outpath, search_str, replace_str)
                return outpath
            elif ext == '.xpt':
                outpath = os.path.join(temp_dir, f"{base}_replaced.xpt")
                process_xpt(data_path, outpath, search_str, replace_str)
                return outpath
            else:
                return None

        if file_ext == '.zip':
            zip_in = os.path.join(temp_dir, uploaded_file.filename)
            uploaded_file.save(zip_in)
            with zipfile.ZipFile(zip_in, 'r') as zin:
                zin.extractall(temp_dir)
                for f in zin.namelist():
                    file_path = os.path.join(temp_dir, f)
                    out = process_one(file_path, f)
                    if out: processed_files.append(out)
        else:
            file_path = os.path.join(temp_dir, uploaded_file.filename)
            uploaded_file.save(file_path)
            out = process_one(file_path, uploaded_file.filename)
            if out: processed_files.append(out)

        zip_path = os.path.join(temp_dir, "replaced_files.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for f in processed_files:
                zout.write(f, arcname=os.path.basename(f))

        return send_file(zip_path, as_attachment=True, download_name="replaced_files.zip")

    return render_template('index_multi_simple.html')

if __name__ == '__main__':
    # --- This is the only important change for Railway ---
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
