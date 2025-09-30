# Twilio IVR Admission System

This project is a **Flask-based IVR (Interactive Voice Response) system** for collecting student admission details via phone calls using Twilio. It records responses, saves them locally, and maintains an in-memory student data store.

---

## Features

- Make outbound calls to students automatically.
- Interactive IVR with speech recording.
- Collects:
  - Program of interest
  - Hostel requirement
  - Scholarship interest
  - Name
  - Age
- Stores recordings locally.
- Logs collected student data with timestamps.

---

## Prerequisites

1. Python 3.8+
2. Twilio Account  
   - [Sign up for Twilio](https://www.twilio.com/try-twilio)
3. Flask and dependencies:

```bash
pip install Flask twilio requests
Environment variables:

bash
Copy code
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number
Setup
Clone the repository:

bash
Copy code
git clone <repository-url>
cd <repository-folder>
Set up your environment variables:

bash
Copy code
export TWILIO_ACCOUNT_SID="ACxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_PHONE_NUMBER="+1XXXXXXXXXX"
On Windows (PowerShell):

powershell
Copy code
setx TWILIO_ACCOUNT_SID "ACxxxxxx"
setx TWILIO_AUTH_TOKEN "your_auth_token"
setx TWILIO_PHONE_NUMBER "+1XXXXXXXXXX"
Create a folder to store recordings:

bash
Copy code
mkdir recordings
Update local_folder path in app.py if necessary:

python
Copy code
local_folder = r"C:\Users\YourName\recordings"
Running the Application
Start the Flask server:

bash
Copy code
python call_app.py
The server will run at: http://127.0.0.1:5000

API Endpoints
1. Make a Call
vbnet
Copy code
GET /make_call?to=+91XXXXXXXXXX
to: The phone number of the student (with country code).

2. IVR Flow
/voice – Initial IVR greeting.

/gather_input – Handles key press input from IVR.

/save_response?field=<field_name> – Saves recorded responses.

Fields collected in order:

Program (program)

Hostel requirement (hostel)

Scholarship (scholarship)

Name (name)

Age (age)

Data Storage
In-memory dictionary for student responses: student_data.

Recordings stored locally in recordings folder.

Each file named as <CallSID>_<field>.wav.

Example:

makefile
Copy code
C:\Users\YourName\recordings\CA1234567890_program.wav
Logging
All call actions and recorded files are logged using Python’s logging module.

Notes
This is a development version; do not use in production without proper security measures.

Recording duration is limited via max_length in the code.

Make sure your Twilio number has outbound call capability and sufficient balance.