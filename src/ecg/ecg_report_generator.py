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

    html = f"""
    <html>
    <head>
    <style>
       
   body {{
            font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
            background: #ffffff;
            color: #222;
            margin: 0;
            padding: 0;
        }}
        .report-container {{
            margin: 40px;
            border: 3px solid #2453ff; /* Clean blue border */
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(36, 83, 255, 0.1);
            background: #fff;
        }}
        .header-bar {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            padding: 32px 48px 18px 48px;
            background: linear-gradient(90deg, #eaf0ff 0%, #fffbe7 100%);
            border-radius: 0 0 32px 32px;
            box-shadow: 0 2px 16px #2453ff22;
        }}
        .header-title {{
           font-family: Georgia, serif;
           font-size: 400px;               
           font-weight: 900;              
           color: #0E2148;                
           letter-spacing: 2px;           
           text-transform: uppercase;     
           text-align: left;              
           padding:10px 0;
           border-bottom: 4px solid #ff6600;
        }}
        .header-date {{
            font-size: 200px;
            color: #000000;
            font-weight: 500;
            text-align: right;
        }}
        .section {{
             margin: 36px auto 0 auto;
             max-width: 820px;
             background: linear-gradient(145deg, #eaf0ff, #ffffff); /* Soft blue-white blend */
             border-radius: 24px;
             box-shadow: 0 4px 28px rgba(36, 83, 255, 0.15);         /* Softer shadow */
             padding: 38px 48px;
             border: 1px solid #2453ff33;  
             color: #1A2A80;
        }}
        .section-title {{
           color: #000000;
           font-size:300px;
           font-weight: bold;
           margin-bottom: 18px;
           border-bottom: 2px solid #ff6600;
           padding-bottom: 8px;
           text-align: left;
        }}
        
        .data-table, .metrics-table {{
            margin-top: 28px; /* Add this for gap above the table */
            /* ...existing code... */
        }}
        .data-table {{
             width: 300%;
             border-collapse: separate;
             border-spacing: 0;
             margin-bottom: 28px;
             font-size: 1.13em;
             background: #ffffff;
             border-radius: 12px;
             overflow: hidden;
             box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
             border: 1px solid #e0e0e0;
        }}
        .data-table th {{
           padding: 16px 28px;
           text-align: left;
           white-space: nowrap;
        }}
        .data-table td {{
           padding: 16px 28px;
           text-align: left;
           white-space: nowrap;
        }}
        
         .data-table th {{
          border-bottom: 1px solid #ddd;
        }}
        
        .data-table tr{{
            border-bottom: none;
        }}
        
        .metrics-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 1.1em;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 16px rgba(0, 0, 0, 0.07);
            margin: 30px 0;
        }}
        .metrics-table th, 
        .metrics-table td {{
            padding: 20px 40px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
       .metrics-table th {{
           background-color: #f9f9f9;
           font-weight: bold;
           color: #333333;
           border-bottom: 2px solid #ff6600;
        }}
        .metrics-table tr:nth-child(even) td {{
            background-color: #fcfcfc;
        }}        
        .metrics-table tr:hover td {{
            background-color: #f2faff;
        }}        
        .metrics-table td {{
            color: #222;
        }}
        
        
        # .wide-col {{
        # min-width: 300px;  /* adjust width as needed */
        # }}
        # .metrics-table tr:nth-child(even) td {{
        #     background: #f7faff;
        # }}
        # .metrics-table tr:nth-child(odd) td {{
        #     background: #fff;
        # }}
        
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
            margin-bottom: 6px;
            font-size: 100em;
        }}
        .lead-img {{
            border: 2.5px solid #2453ff;
            border-radius: 12px;
            background: #fff;
            max-width: 95%;
            max-height: 350px;
            margin: 0 auto 0 auto;
            display: block;
        }}
        
       .conclusion-section {{
    margin: 40px auto;
    padding: 32px 48px;
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    font-family: Georgia, serif;
    color: #222;
    max-width: 800px;
}}

.conclusion-title,
.recommendations-title {{
    font-size: 1.5em;
    font-weight: bold;
    color: #000;
    margin-bottom: 12px;
    border-bottom: 2px solid #ff6600;
    padding-bottom: 6px;
}}

.conclusion-text {{
    font-size: 1.1em;
    margin-bottom: 32px;
    line-height: 1.6;
}}

.recommendations-section {{
    margin-bottom: 32px;
}}

.recommendations-list {{
    padding-left: 20px;
    line-height: 1.6;
}}

.disclaimer {{
    font-size: 0.95em;
    background: #fffbe7;
    padding: 16px;
    border-left: 4px solid #ffaa00;
    border-radius: 8px;
    line-height: 1.5;
}}

.disclaimer-label {{
    font-weight: bold;
    color: #aa0000;
}}

    </style>
    </head>
    <body>
       <div class="report-container">
        <div class="header-bar">
            <div class="header-title">{test_name}</div>
            <div class="header-date">{date_time}</div>
        </div>
        <div class="section">
            <div class="section-title">Patient Details</div>
            <table class="data-table">
                 <tr>
                    <th class="wide-col"><b>First Name:<b> {first_name}</th>
                    <th class="wide-col">Last Name: {last_name}</th>
                    <th class="wide-col">Age: {age}</th>
                    <th class="wide-col">Gender:{gender}</th>
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
    """

     # --- 12 LEAD GRAPHS, 2 PER PAGE ---
    lead_order = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
    if lead_img_paths:
        for i in range(0, len(lead_order), 4):
            html += '<div style="display: flex; flex-direction: column; align-items: center;">'
            for j in range(4):
                if i + j < len(lead_order):
                    lead = lead_order[i + j]
                    img_path = lead_img_paths.get(lead)
                    if img_path and os.path.exists(img_path):
                        html += f"""
                        <div class="lead-block" style="padding-bottom:0;">
                            <div class="lead-label" style="font-size:300px;">{lead}</div>
                            <img src="{img_path}" class="lead-img" alt="{lead} Graph" height="250" width="550">
                        </div>
                        """
            html += '</div>'
            html += '<div class="page-break"></div>'

    # --- CONCLUSION SECTION (Last Page) ---
    html += """
        <div class="conclusion-section">
    <div class="conclusion-title">Conclusion</div>
    <div class="conclusion-text">
        This ECG report is generated automatically. Please consult your physician for a detailed diagnosis.
    </div>

    <div class="recommendations-section">
        <div class="recommendations-title">Recommendations</div>
        <ul class="recommendations-list">
            <li>Consult your physician for a detailed diagnosis.</li>
            <li>Repeat ECG if symptoms persist or worsen.</li>
            <li>Maintain a healthy lifestyle and regular checkups.</li>
        </ul>
    </div>

    <div class="disclaimer">
        <span class="disclaimer-label">Disclaimer:</span>
        This ECG report is an interpretation of electrical parameters and may vary over time. 
        <b>PLEASE CONSULT YOUR PHYSICIAN FOR DIAGNOSIS.</b>
    </div>
</div>

    </body>
    </html>
    """

    return html