from flask import Flask, render_template, request, send_file, url_for
import os
import joblib
import numpy as np
import io
import datetime
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ===== UNIVERSAL PATHS (Render, Railway, Heroku, Local sab chalega) =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "best_soil_model.pkl")
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER)

# Load model
try:
    model = joblib.load(MODEL_PATH)
    print("Model loaded → Ready to predict!")
except Exception as e:
    print("MODEL LOAD ERROR →", e)
    model = None

# Recommendation function
def get_recommendation(pred_pct, inputs):
    NO3, NH4, P, K, SO4, B, OM, pH, Zn, Cu, Fe, Ca, Mg, Na = inputs
    N = NO3 + NH4
    rec = "<ul class='space-y-4 text-lg'>"
    
    if N < 50:
        rec += "<li class='text-orange-500'>Apply <strong>Urea</strong>: 150–200 kg/ha</li>"
    elif N < 80:
        rec += "<li class='text-yellow-500'>Apply <strong>Urea</strong>: 80–120 kg/ha</li>"
    else:
        rec += "<li class='text-green-500'>Nitrogen sufficient</li>"

    if P < 80:
        rec += "<li class='text-orange-500'>Apply <strong>DAP</strong>: 100–180 kg/ha</li>"
    elif P < 140:
        rec += "<li class='text-yellow-500'>Apply <strong>DAP</strong>: 50–100 kg/ha</li>"
    else:
        rec += "<li class='text-green-500'>Phosphorus adequate</li>"

    if K < 150:
        rec += "<li class='text-orange-500'>Apply <strong>MOP</strong>: 100–150 kg/ha</li>"
    elif K < 220:
        rec += "<li class='text-yellow-500'>Apply <strong>MOP</strong>: 50–80 kg/ha</li>"
    else:
        rec += "<li class='text-green-500'>Potassium sufficient</li>"

    if OM < 3:
        rec += "<li class='text-orange-500'>Add <strong>FYM/Compost</strong>: 10–15 tons/ha</li>"
    elif OM < 5:
        rec += "<li class='text-yellow-500'>Add <strong>FYM</strong>: 5–8 tons/ha</li>"
    else:
        rec += "<li class='text-green-500'>Organic Matter good</li>"

    if pH < 6.0:
        rec += "<li class='text-orange-500'>Apply <strong>Lime</strong>: 2–5 tons/ha</li>"
    elif pH > 7.8:
        rec += "<li class='text-orange-500'>Apply <strong>Gypsum</strong> to reduce pH</li>"
    else:
        rec += "<li class='text-green-500'>pH is perfect</li>"

    rec += "<li class='text-emerald-600 font-bold mt-6'>Target: Ultra-Fertile in one season!</li>"
    rec += "</ul>"
    return rec

@app.route("/", methods=["GET", "POST"])
@app.route("/predict", methods=["POST"])
def index():
    error = None
    prediction = None
    status = None
    recommendation = None

    if request.method == "POST":
        try:
            inputs = [float(request.form.get(k, 0)) for k in ["NO3","NH4","P","K","SO4","B","OM","pH","Zn","Cu","Fe","Ca","Mg","Na"]]
            final_input = np.array([inputs])
            raw_score = model.predict(final_input)[0]
            prediction = round(float(raw_score), 1)
            prediction = max(0, min(100, prediction))

            if prediction >= 98:
                status = "Ultra-Fertile"
            elif prediction >= 88:
                status = "Very Good"
            elif prediction >= 75:
                status = "Average Soil"
            elif prediction >= 55:
                status = "Needs Improvement"
            else:
                status = "Poor / Deficient"

            recommendation = get_recommendation(prediction, inputs)

        except Exception as e:
            error = "Please fill all fields correctly!"
            print(e)

    return render_template("index.html", prediction=prediction, status=status, recommendation=recommendation, error=error)

@app.route("/test_cases")
def test_cases():
    return render_template("test_cases.html")

@app.route("/download_report")
def download_report():
    try:
        pred = request.args.get("pred")
        status = request.args.get("status")
        rec_html = request.args.get("rec", "")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=70, bottomMargin=70, leftMargin=70, rightMargin=70)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Soil Fertility Analysis Report", styles['Title']))
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"Date: {datetime.datetime.now().strftime('%d %B %Y, %I:%M %p')}", styles['Normal']))
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"<b>Score:</b> {pred}%", styles['Heading2']))
        story.append(Paragraph(f"<b>Status:</b> <font color='green'>{status}</font>", styles['Normal']))
        story.append(Spacer(1, 20))

        if rec_html:
            story.append(Paragraph("<b>Recommendations:</b>", styles['Heading3']))
            story.append(Spacer(1, 10))
            items = re.findall(r'<li[^>]*>(.*?)</li>', rec_html)
            for item in items:
                clean = re.sub('<.*?>', '', item)
                story.append(Paragraph(f"• {clean}", styles['Normal']))
                story.append(Spacer(1, 6))

        story.append(Spacer(1, 50))
        story.append(Paragraph("Thank you for using Soil Fertility Predict!", styles['Normal']))
        story.append(Paragraph("Developed by Nitin & Team", styles['Italic']))

        doc.build(story)
        buffer.seek(0)

        return send_file(buffer, as_attachment=True,
                         download_name=f"Soil_Report_{datetime.datetime.now().strftime('%d%m%Y_%H%M')}.pdf",
                         mimetype="application/pdf")
    except Exception as e:
        print("PDF Error:", e)
        return "PDF generation failed", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)