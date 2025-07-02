# ECG Monitor Software

This project is an ECG monitor software that provides a comprehensive solution for conducting 12-lead ECG tests, recording ECG data, and analyzing heartbeat statistics. The application features a user-friendly interface with a splash screen, user authentication, and a dashboard for displaying ECG data.

## Features

- **Splash Screen**: A visually appealing splash screen that appears during application startup.
- **User Authentication**: Secure sign-in and sign-out functionality for users.
- **ECG Recording**: Ability to start, stop, and save ECG recordings.
- **12-Lead ECG Test**: Conduct and analyze a 12-lead ECG test.
- **Dashboard**: A dashboard that displays saved lead waves, heartbeat data, and monthly ECG statistics.

## Project Structure

```
ecg-monitor
├── src
│   ├── main.py
│   ├── splash_screen.py
│   ├── auth
│   │   ├── sign_in.py
│   │   └── sign_out.py
│   ├── ecg
│   │   ├── recording.py
│   │   └── twelve_lead_test.py
│   ├── dashboard
│   │   ├── saved_leads.py
│   │   ├── heartbeat_data.py
│   │   └── monthly_statistics.py
│   └── utils
│       └── helpers.py
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd ecg-monitor
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python src/main.py
   ```
2. Follow the on-screen instructions to sign in or sign out.
3. Use the dashboard to access ECG recording features and view statistics.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.