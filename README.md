# ECG Monitor Software

A modern, modular ECG monitor app for 12-lead ECG tests, real-time recording, and advanced dashboard analytics. Features a beautiful, responsive UI/UX with dark mode, animated splash, and robust authentication.

## Features

- **Animated Splash Screen**: Modern, centered, always-on-top splash with GIF animation.
- **Authentication**: Modular sign in/sign up with two-column, Instagram-style dialog. Supports email and phone login.
- **Dashboard**: Personalized greeting, heartbeat animation, ECG chart (shows real Lead II data if available), pie chart, calendar with last ECG date highlight, and medical/dark mode toggles.
- **12-Lead ECG Test**: Standalone window for live 12-lead test, with menu actions (Save/Open/Export/Print/Back). Writes Lead II data for dashboard.
- **Dark Mode**: All dashboard blocks/widgets adapt to dark mode with white borders and seamless black backgrounds.
- **Medical Mode**: Blue/green/white color coding for clinical use.
- **Responsive UI**: All dialogs and windows are centered and adapt to resizing. No fixed sizes; uses size policies and stretches.
- **Robust Menu**: Modular ECGMenu for all test actions.
- **Live Data Sharing**: Dashboard ECG chart auto-updates from test page via `lead_ii_live.json`.

## Project Structure

```
EcgFR/
├── src/
│   ├── main.py
│   ├── splash_screen.py
│   ├── auth/
│   │   ├── sign_in.py
│   │   └── sign_out.py
│   ├── dashboard/
│   │   └── dashboard.py
│   ├── ecg/
│   │   ├── recording.py
│   │   └── twelve_lead_test.py
│   └── utils/
│       └── helpers.py
├── assets/  # All images, GIFs, etc.
├── users.json
├── lead_ii_live.json
├── last_ecg_date.json
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository:
   ```sh
   git clone <repository-url>
   cd EcgFR
   ```
2. (Recommended) Create a virtual environment:
   ```sh
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```sh
   python src/main.py
   ```
2. Sign in or sign up. Use the dashboard to view live ECG, statistics, and run a 12-lead test.
3. Use the dark mode/medical mode toggles for different UI themes.
4. All data is stored locally in JSON files.

## Notes
- For best experience, use on Windows with all assets present in the `assets/` folder.
- The dashboard ECG chart will show a mock wave if no real Lead II data is available.
- Menu actions in the 12-lead test window are modular and can be extended.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.