import os

def generate_ecg_html_report(
    HR, PR, QRS, QT, QTc, ST,
    test_name, date_time,
    first_name, last_name, age, gender,
    abnormal_report, text, obstext, qrstext,
    uId, testId, dataId,
    lead_img_paths = {
        "I": "lead_I.png",
        "II": "lead_II.png",
        "III": "lead_III.png",
        "aVR": "lead_aVR.png",
        "aVL": "lead_aVL.png",
        "aVF": "lead_aVF.png",
        "V1": "lead_V1.png",
        "V2": "lead_V2.png",
        "V3": "lead_V3.png",
        "V4": "lead_V4.png",
        "V5": "lead_V5.png",
        "V6": "lead_V6.png"
    },
    QRS_axis = None
):
    def to_float(val):
        try:
            return float(val)
        except Exception:
            return 0

    HR = to_float(HR)
    PR = to_float(PR)
    QRS = to_float(QRS)
    QT = to_float(QT)
    QTc = to_float(QTc)
    ST = to_float(ST)

    # --- HTML HEADER ---
    html = f"""
    <html>
    <head>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
            background: #f7f7f7;
            color: #222;
            margin: 0;
            padding: 0;
        }}
        .header-bar {{
            background: linear-gradient(90deg, #2453ff 0%, #ff6600 100%);
            color: #222;
            padding: 32px 0 18px 0;
            text-align: center;
            border-radius: 0 0 32px 32px;
            box-shadow: 0 2px 16px #2453ff44;
        }}
        .header-bar h1 {{
            color: #222;
            margin: 0;
            font-size: 2.6em;
            letter-spacing: 2px;
            font-weight: bold;
            text-shadow: 0 2px 12px #0004;
        }}
        .header-bar h3 {{
            color: #222;
            margin: 10px 0 0 0;
            font-weight: normal;
            font-size: 1.2em;
            text-shadow: 0 1px 6px #0002;
        }}
        .first-section {{
            background: linear-gradient(120deg, #eaf0ff 0%, #fffbe7 100%);
            margin: 36px auto 0 auto;
            border-radius: 24px;
            box-shadow: 0 2px 24px #2453ff22;
            max-width: 820px;
            padding: 38px 48px 38px 48px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .section-title {{
            color: #2453ff;
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 22px;
            border-bottom: 2px solid #ff6600;
            padding-bottom: 8px;
            width: 100%;
            text-align: left;
        }}
        .patient-table, .metrics-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0 0 28px 0;
            font-size: 1.13em;
            background: #fff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 8px #2453ff11;
        }}
        .patient-table th, .metrics-table th {{
            background: #2453ff;
            color: #fff;
            padding: 12px 10px;
            font-weight: bold;
            font-size: 1.08em;
        }}
        .patient-table td, .metrics-table td {{
            padding: 12px 10px;
            border-bottom: 1px solid #eee;
            text-align: center;
        }}
        .patient-table tr:last-child td, .metrics-table tr:last-child td {{
            border-bottom: none;
        }}
        .metrics-table tr:nth-child(even) {{
            background: #f7faff;
        }}
        .metrics-table tr:nth-child(odd) {{
            background: #fff;
        }}
        .page-break {{
            page-break-after: always;
        }}
        .lead-block {{
            margin: 0 auto 20px auto;
            max-width: 700px;
            background: #fff;
            border-radius: 14px;
            box-shadow: 0 2px 12px #ff660022;
            padding: 18px 18px 18px 18px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .lead-label {{
            text-align: center;
            font-weight: bold;
            color: #2453ff;
            margin-bottom: 3px;
            font-size: 1.1em;
        }}
        .lead-img {{
            border: 2.5px solid #2453ff;
            border-radius: 12px;
            background: #fff;
            max-width: 95%;
            max-height: 320px;
            margin: 0 auto 0 auto;
            display: block;
        }}
        .conclusion, .recommendations {{
            margin-top: 18px;
            font-size: 1.08em;
        }}
        .conclusion-title, .recommendations-title {{
            color: #ff6600;
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 1.13em;
            text-decoration: underline;
        }}
        .disclaimer {{
            margin-top: 24px;
            font-size: 0.98em;
            color: #888;
            background: #fffbe7;
            border-radius: 8px;
            padding: 10px 18px;
            border-left: 4px solid #ff6600;
        }}
    </style>
    </head>
    <body>
        <div class="header-bar">
            <h1>{test_name}</h1>
            <h3>Date: {date_time}</h3>
        </div>
        <div class="first-section">
            <div class="section-title">Patient Details</div>
            <table class="patient-table">
                <tr>
                    <th>First Name</th>
                    <th>Last Name</th>
                    <th>Age</th>
                    <th>Gender</th>
                </tr>
                <tr>
                    <td>{first_name}</td>
                    <td>{last_name}</td>
                    <td>{age}</td>
                    <td>{gender}</td>
                </tr>
            </table>
            <div class="section-title">Observed Values</div>
            <table class="metrics-table">
                <tr>
                    <th>Parameter</th>
                    <th>Observed</th>
                    <th>Standard Range</th>
                </tr>
                <tr><td>Heart Rate</td><td>{HR} bpm</td><td>60 - 100 bpm</td></tr>
                <tr><td>PR Interval</td><td>{PR} ms</td><td>120 - 200 ms</td></tr>
                <tr><td>QRS Complex</td><td>{QRS} ms</td><td>70 - 120 ms</td></tr>
                <tr><td>QT Interval</td><td>{QT} ms</td><td>300 - 450 ms</td></tr>
                <tr><td>QTc Interval</td><td>{QTc} ms</td><td>300 - 450 ms</td></tr>
                <tr><td>ST Segment</td><td>{ST} ms</td><td>80 - 120 ms</td></tr>
                <tr><td>QRS Axis</td><td>{'Not Available' if QRS_axis is None else QRS_axis}</td><td>Typically -30° to +90°</td></tr>
            </table>
        </div>
        <div class="page-break"></div>
    """

    # --- 12 LEAD GRAPHS, 2 PER PAGE ---
    lead_order = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
    if lead_img_paths:
        for i in range(0, len(lead_order), 2):
            html += '<div style="display: flex; flex-direction: column; align-items: center;">'
            for j in range(2):
                if i + j < len(lead_order):
                    lead = lead_order[i + j]
                    img_path = lead_img_paths.get(lead)
                    if img_path and os.path.exists(img_path):
                        html += f"""
                        <div class="lead-block" style="padding-bottom:0;">
                            <div class="lead-label" style="font-size:1em;">{lead}</div>
                            <img src="{img_path}" class="lead-img" alt="{lead} Graph" height="200" width="500">
                        </div>
                        """
            html += '</div>'
            html += '<div class="page-break"></div>'

    # --- CONCLUSION SECTION (Last Page) ---
    html += """
        <div class="section">
            <div class="conclusion">
                <div class="conclusion-title">Conclusion</div>
                <div>
                    This ECG report is generated automatically. Please consult your physician for a detailed diagnosis.
                </div>
                <div class="recommendations">
                    <div class="recommendations-title">Recommendations</div>
                    <ul>
                        <li>Consult your physician for a detailed diagnosis.</li>
                        <li>Repeat ECG if symptoms persist or worsen.</li>
                        <li>Maintain a healthy lifestyle and regular checkups.</li>
                    </ul>
                </div>
                <div class="disclaimer">
                    Disclaimer: This ECG report is an interpretation of electrical parameters and may vary over time. <b>PLEASE CONSULT YOUR PHYSICIAN FOR DIAGNOSIS.</b>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return html