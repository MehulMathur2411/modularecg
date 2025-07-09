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
    
    html = ""
    html += "<table style='width:700px;margin-top:-10px;padding-top:-60px;padding-left:-50px;'>"
    html += "<tr>"
    html += "<td>"
    html += f"<h2 style='position: absolute; top: 1%; left: 42.7%; transform: translate(-50%, -50%);color:#fff;font-size:19px'>Heart rate</h2>"
    html += f"<h2 style='position: absolute; top: 3.4%; left: 41%; transform: translate(-50%, -50%);color:#fff;font-size:29px'>{HR} bpm</h2>"
    html += "<img src='graph_img/rlogo.png' width='460px'/>"
    html += "</td>"
    html += "<td style='text-align: center;'>"
    html += f"<h2 style='margin: 0px;'>{test_name}</h2>"
    html += f"<h5 style='margin: 0px;'>Date : {date_time}</h5>"
    html += "</td>"
    html += "</tr>"
    html += "</table>"

    html += "<h3 style='margin-top: 20px;padding-left:-30px;'>Patient Details</h3>"
    html += "<table style='width:700px;'>"
    html += "<tr>"
    html += f"<td>Full Name: {first_name}</td>"
    html += f"<td>Age: {age} years</td>"
    html += "</tr>"
    html += "<tr>"
    html += f"<td>Last Name : {last_name}</td>"
    html += f"<td>Height : {height} cms</td>"
    html += "</tr>"
    html += "<tr>"
    html += f"<td>Gender : {gender}</td>"
    html += f"<td>Weight : {weight} kgs</td>"
    html += "</tr>"
    html += "</table>"

    html += "<br><h3 style='margin-top: 10px;padding-left:-30px;'>OBSERVATIONS</h3><br>"

    # --- Observations Section ---
    html += "<br><br><h4 style='margin-top: 10px;margin-bottom:12px;'>Lead II Graph:</h4>"
    html += "<div style='text-align:center; margin: 10px 0 20px 0;'>"
    if lead2_img_path and os.path.exists(lead2_img_path):
        html += f"<img src='{lead2_img_path}' style='border:2px solid #2453ff; border-radius:10px; background:#fff;' alt='Lead II Graph'><br>"
    else:
        graphLink = f"graphPage.php?uid={uId}&test_id={testId}&dataId={dataId}"
        html += f"<img src='{graphLink}' style='border:2px solid #2453ff; border-radius:10px; background:#fff;' alt='Lead II Graph'><br>"
    html += "</div>"
        
    # --- Add the live metrics table here ---
    html += "<h3 style='margin-top: 20px;'>Observed Values</h3>"
    html += "<table style='width:500px;border:1px solid #ff6600;border-radius:8px;padding:8px;font-size:16px;'>"
    html += "<tr><th style='text-align:left;'>Parameter</th><th>Observed</th><th>Standard Range</th></tr>"
    html += f"<tr><td>Heart Rate</td><td>{HR} bpm</td><td>60 - 100 bpm</td></tr>"
    html += f"<tr><td>PR Interval</td><td>{PR} ms</td><td>120 - 200 ms</td></tr>"
    html += f"<tr><td>QRS Complex</td><td>{QRS} ms</td><td>70 - 120 ms</td></tr>"
    html += f"<tr><td>QT Interval</td><td>{QT} ms</td><td>300 - 450 ms</td></tr>"
    html += f"<tr><td>QTc Interval</td><td>{QTc} ms</td><td>300 - 450 ms</td></tr>"
    html += f"<tr><td>ST Segment</td><td>{ST} ms</td><td>80 - 120 ms</td></tr>"
    html += f"<tr><td>QRS Axis</td><td>{'Not Available' if QRS_axis is None else QRS_axis}</td><td>Typically -30° to +90°</td></tr>"
    html += "</table>"

    html += "<h6 style='margin-top: 7px; margin-bottom:7px;padding-bottom:7px;'>Disclaimer: This ECG report generated is the interpretation of electrical parameters. Hence, it can vary in respect of time. PLEASE CONSULT YOUR PHYSICIAN FOR DIAGNOSIS </h6>"

    html += "<br><br><h4 style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'><u>CONCLUSION :<u></h4>"

    if abnormal_report == 'N':
        # Heart rate
        if 60 <= HR <= 100:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>1. Heart rate is normal.</div>"
        else:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>1. Heart rate is abnormal.</div>"

        # PR interval
        if 120 <= PR <= 200:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>2. PR interval is normal.</div>"
        elif PR > 200:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>2. PR interval is > 200 ms, first degree heart block is said to be present.</div>"
        elif PR < 120:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>2. PR interval < 120 ms suggests pre-excitation (the presence of an accessory pathway between the atria and ventricles)</div>"

        # QRS
        if 70 <= QRS <= 100:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>3. QRS Interval is normal.</div>"
        elif QRS < 70:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>3. Narrow QRS Interval Detected.</div>"
        elif QRS >= 100:
            if QRS <= 120:
                html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>3. QRS interval is abnormal.</div>"
            if QRS > 120:
                html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>3. QRS duration > 120 ms is required for the diagnosis of bundle branch block or ventricular rhythm.</div>"

        # QT
        if 300 <= QT <= 450:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>4. QT is normal.</div>"
        else:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>4. QT is abnormal.</div>"

        # QTc
        if 300 <= QTc <= 450:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>5. QTc is normal.</div>"
        elif 450 <= QTc <= 500:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>5. QTc is prolonged.</div>"
        elif QTc > 500:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>5. QTc > 500 is associated with an increased risk of torsades de pointes.</div>"
        elif QTc < 300:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>5. QTc is abnormally shorted.</div>"

        # ST
        if 80 <= ST <= 120:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>6. ST is normal.</div>"
        else:
            html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;color: red;'>6. ST is abnormal.</div>"

        # Additional text
        if text:
            html += f"<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>{text}</div>"
        if obstext:
            html += f"<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>{obstext}</div>"
        if qrstext:
            html += f"<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>{qrstext}</div>"

    else:
        html += "<div style='margin-top: 17px;margin-bottom:7px;padding-bottom:7px;'>Invalid Test. Kindly Reconnect The Device And Try Again..!</div>"

    html += "<br><h4 style='margin-top: 7px;margin-bottom:7px;padding-bottom:7px;'><u>RECOMMENDATIONS :</u></h4><br><br><br><br>"

    # You can add more recommendations or sections as needed

    return html