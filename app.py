from flask import Flask, request, render_template_string, send_file
from pathlib import Path
from datetime import datetime
import cv2, numpy as np, io, csv
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
BASE = Path(__file__).resolve().parent
OUTPUT = BASE / 'results'
OUTPUT.mkdir(exist_ok=True)

PAGE = '''<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Tablet Counter</title><style>
body{font-family:system-ui,sans-serif;background:#101923;color:#eef4fa;margin:0;padding:20px}main{max-width:650px;margin:auto}h1{margin-bottom:5px}.muted{color:#a9b9c8}.card{background:#1d2b39;border-radius:14px;padding:20px;margin:16px 0}label{display:block;margin:14px 0 5px}input,select,button{box-sizing:border-box;width:100%;font:inherit;border-radius:8px;padding:12px;border:1px solid #64798c}button{background:#42d8a2;border:0;color:#08241a;font-weight:700;margin-top:20px}img{max-width:100%;border-radius:8px}.count{font-size:64px;font-weight:800;color:#42d8a2}a{color:#42d8a2}.warn{color:#f4c978}</style></head><body><main><h1>Tablet Counter</h1><div class="muted">Local demonstration • Analyst verification required</div><div class="card"><form action="/count" method="post" enctype="multipart/form-data"><label>Case number</label><input name="case" maxlength="80" required><label>Item number</label><input name="item" maxlength="80" required><label>Analyst</label><input name="analyst" maxlength="80" required><label>Tablet color relative to background</label><select name="polarity"><option value="auto">Automatic (try both)</option><option value="light">Light tablets on dark background</option><option value="dark">Dark tablets on light background</option></select><label>Select photo from library</label><input name="photo" type="file" accept="image/*" required><button>Count tablets</button></form></div><p class="muted">Spread tablets apart, use even lighting, avoid shadows, and keep all tablets in the photograph.</p></main></body></html>'''

RESULT = '''<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Count result</title><style>body{font-family:system-ui,sans-serif;background:#101923;color:#eef4fa;padding:18px}main{max-width:800px;margin:auto}img{width:100%;height:auto}a{color:#42d8a2}.count{font-size:60px;color:#42d8a2;font-weight:800}.warn{color:#f4c978}</style></head><body><main><h1>Count result</h1><div class="count">{{ count }}</div><p>Detected objects • <strong>verify each numbered outline</strong></p><p>Case: {{ case }} | Item: {{ item }} | Analyst: {{ analyst }}</p><img src="/result/{{ filename }}"><p><a href="/result/{{ filename }}" download>Save annotated photograph</a></p><p class="warn">Demonstration only. Not validated for evidentiary use. Confirm count manually.</p><p><a href="/">Count another image</a></p></main></body></html>'''

from flask import render_template_string

@app.get('/')
def index():
    return render_template_string(PAGE)

@app.get('/result/<name>')
def result_file(name):
    if secure_filename(name) != name or not name.endswith('.jpg'):
        return 'Invalid filename', 400
    path = OUTPUT / name
    if not path.is_file():
        return 'Not found', 404
    return send_file(path, mimetype='image/jpeg')

def find_objects(image, polarity):
    h, w = image.shape[:2]
    scale = min(1.0, 1600 / max(h,w))
    small = cv2.resize(image, None, fx=scale, fy=scale) if scale < 1 else image.copy()
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5,5), 0)
    # Otsu handles relatively uniform, contrasting backgrounds.
    _, base = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    masks = {'light':base, 'dark':cv2.bitwise_not(base)}
    candidates = []
    for kind, mask in masks.items():
        if polarity != 'auto' and kind != polarity:
            continue
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area = mask.shape[0]*mask.shape[1]
        valid = []
        for c in contours:
            a = cv2.contourArea(c)
            x,y,cw,ch = cv2.boundingRect(c)
            if a < area*0.00012 or a > area*0.12:
                continue
            if x <= 1 or y <= 1 or x+cw >= mask.shape[1]-1 or y+ch >= mask.shape[0]-1:
                continue
            if min(cw,ch) < 5:
                continue
            valid.append(c)
        # In automatic mode, favor the polarity with fewer foreground pixels and
        # reasonable separate objects; not guaranteed for every image.
        foreground = np.count_nonzero(mask)/area
        score = len(valid) - 30*max(0, foreground-0.35)
        candidates.append((score, valid, kind))
    if not candidates:
        return small, [], 'none'
    _, contours, chosen = max(candidates, key=lambda t:t[0])
    contours.sort(key=lambda c:(cv2.boundingRect(c)[1]//60, cv2.boundingRect(c)[0]))
    annotated = small.copy()
    for i,c in enumerate(contours,1):
        cv2.drawContours(annotated, [c], -1, (0,255,0), 3)
        m = cv2.moments(c)
        if m['m00']:
            x,y = int(m['m10']/m['m00']),int(m['m01']/m['m00'])
        else:
            x,y,_,_ = cv2.boundingRect(c)
        cv2.putText(annotated,str(i),(x,y),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,0),5,cv2.LINE_AA)
        cv2.putText(annotated,str(i),(x,y),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2,cv2.LINE_AA)
    return annotated, contours, chosen

@app.post('/count')
def count():
    photo = request.files.get('photo')
    if not photo:
        return 'No photograph uploaded',400
    raw = photo.read()
    if not raw:
        return 'Empty photograph',400
    data = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        return 'Could not read image. Try a JPEG or PNG photograph.',400
    polarity = request.form.get('polarity','auto')
    if polarity not in ('auto','light','dark'):
        polarity = 'auto'
    annotated, objects, chosen = find_objects(image,polarity)
    fields = {k:request.form.get(k,'').strip()[:80] for k in ('case','item','analyst')}
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filename = f'count_{stamp}.jpg'
    cv2.imwrite(str(OUTPUT/filename),annotated)
    with (OUTPUT/'counts.csv').open('a',newline='') as f:
        csv.writer(f).writerow([datetime.now().isoformat(timespec='seconds'),fields['case'],fields['item'],fields['analyst'],len(objects),chosen,filename])
    return render_template_string(RESULT, count=len(objects), filename=filename, **fields)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
