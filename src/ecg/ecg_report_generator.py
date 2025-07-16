import os

def generate_ecg_html_report(
    HR, PR, QRS, QT, QTc, ST,
    test_name, date_time,
    first_name, last_name, age, height, gender, weight,
    abnormal_report, text, obstext, qrstext,
    uId, testId, dataId,
    lead2_img_path=None,
    QRS_axis=None
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

    html = """
    <html>
    <head>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            background: #f7f7f7;
            color: #000;
            margin: 0;
            padding: 0;
        }}
        .header-bar {{
            background: linear-gradient(90deg, #ff6600 0%, #ffb347 100%);
            color: #000;
            padding: 24px 0 16px 0;
            text-align: center;
            border-radius: 0 0 24px 24px;
            box-shadow: 0 2px 12px #ff660044;
        }}
        .header-bar h1 {{
            color: #000;
            margin: 0;
            font-size: 2.2em;
            letter-spacing: 2px;
        }}
        .header-bar h3 {{
            color: #000;
            margin: 6px 0 0 0;
            font-weight: normal;
            font-size: 1.1em;
        }}
        .section {{
            background: #fff;
            margin: 32px auto 0 auto;
            border-radius: 18px;
            box-shadow: 0 2px 16px #ff660022;
            max-width: 800px;
            padding: 32px 40px 32px 40px;
        }}
        .section-title {{
            color: #ff6600;
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 18px;
            border-bottom: 2px solid #ffb347;
            padding-bottom: 6px;
        }}
        .patient-info {{
            margin-bottom: 18px;
            font-size: 1.1em;
        }}
        .patient-info td {{
            padding: 6px 18px 6px 0;
        }}
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 18px 0 24px 0;
            font-size: 1.08em;
        }}
        .metrics-table th {{
            background: #ff6600;
            color: #fff;
            padding: 10px 8px;
            font-weight: bold;
            border-radius: 6px 6px 0 0;
        }}
        .metrics-table td {{
            padding: 10px 8px;
            border-bottom: 1px solid #eee;
        }}
        .metrics-table tr:nth-child(even) {{
            background: #fff7f0;
        }}
        .metrics-table tr:nth-child(odd) {{
            background: #fff;
        }}
        .lead-img {{
            display: block;
            margin: 24px auto 18px auto;
            border: 2.5px solid #2453ff;
            border-radius: 12px;
            background: #fff;
            max-width: 95%;
            max-height: 320px;
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
        ...
""".format(
    test_name=test_name,
    date_time=date_time,
    first_name=first_name,
    last_name=last_name,
    age=age,
    height=height,
    gender=gender,
    weight=weight
)

    # ECG image
    if lead2_img_path and os.path.exists(lead2_img_path):
        html += f"<img src='{lead2_img_path}' class='lead-img' alt='Lead II Graph' width='500' height='250'>"
    else:
        graphLink = f"graphPage.php?uid={uId}&test_id={testId}&dataId={dataId}"
        html += f"<img src='{graphLink}' class='lead-img' alt='Lead II Graph' width='500' height='250'>"

    # Metrics Table
    html += """
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
                <tr><td>QRS Axis</td><td>{QRS_axis}</td><td>Typically -30° to +90°</td></tr>
            </table>
    """.format(
        HR=HR, PR=PR, QRS=QRS, QT=QT, QTc=QTc, ST=ST,
        QRS_axis='Not Available' if QRS_axis is None else QRS_axis
    )

    # Conclusion Section
    html += """
            <div class="conclusion">
                <div class="conclusion-title">Conclusion</div>
    """

    if abnormal_report == 'N':
        # Heart rate
        if 60 <= HR <= 100:
            html += "<div>1. Heart rate is normal.</div>"
        else:
            html += "<div style='color: red;'>1. Heart rate is abnormal.</div>"

        # PR interval
        if 120 <= PR <= 200:
            html += "<div>2. PR interval is normal.</div>"
        elif PR > 200:
            html += "<div style='color: red;'>2. PR interval is > 200 ms, first degree heart block is said to be present.</div>"
        elif PR < 120:
            html += "<div style='color: red;'>2. PR interval < 120 ms suggests pre-excitation (the presence of an accessory pathway between the atria and ventricles)</div>"

        # QRS
        if 70 <= QRS <= 100:
            html += "<div>3. QRS Interval is normal.</div>"
        elif QRS < 70:
            html += "<div style='color: red;'>3. Narrow QRS Interval Detected.</div>"
        elif QRS >= 100:
            if QRS <= 120:
                html += "<div>3. QRS interval is abnormal.</div>"
            if QRS > 120:
                html += "<div style='color: red;'>3. QRS duration > 120 ms is required for the diagnosis of bundle branch block or ventricular rhythm.</div>"

        # QT
        if 300 <= QT <= 450:
            html += "<div>4. QT is normal.</div>"
        else:
            html += "<div style='color: red;'>4. QT is abnormal.</div>"

        # QTc
        if 300 <= QTc <= 450:
            html += "<div>5. QTc is normal.</div>"
        elif 450 <= QTc <= 500:
            html += "<div style='color: red;'>5. QTc is prolonged.</div>"
        elif QTc > 500:
            html += "<div style='color: red;'>5. QTc > 500 is associated with an increased risk of torsades de pointes.</div>"
        elif QTc < 300:
            html += "<div style='color: red;'>5. QTc is abnormally shorted.</div>"

        # ST
        if 80 <= ST <= 120:
            html += "<div>6. ST is normal.</div>"
        else:
            html += "<div style='color: red;'>6. ST is abnormal.</div>"

        # Additional text
        if text:
            html += f"<div>{text}</div>"
        if obstext:
            html += f"<div>{obstext}</div>"
        if qrstext:
            html += f"<div>{qrstext}</div>"

    else:
        html += "<div>Invalid Test. Kindly Reconnect The Device And Try Again..!</div>"

    html += "</div>"

    # Recommendations Section
    html += """
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
    </body>
    </html>
    """

    return html