import os
from app import create_app

# Load environment variables if .env exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    print("=======================================================================")
    print("Punjab School Education Department (SED)")
    print("Teacher Service, Seniority & Promotion Management System")
    print("Teacher Promotion Portal - Departmental Promotion Committee (DPC)")
    print("=======================================================================")
    print("Running on http://127.0.0.1:5000")
    print("Accounts Ready for Testing:")
    print("  - SuperAdmin: username 'superadmin' / password 'SuperAdmin@123'")
    print("  - Admin:      username 'admin_lahore' / password 'Admin@123'")
    print("  - Teacher 1:  CNIC '35201-1234567-1' / password 'Teacher@123' (PST -> EST Eligible)")
    print("  - Teacher 2:  CNIC '35201-2345678-2' / password 'Teacher@123' (EST -> SST Eligible)")
    print("  - Teacher 3:  CNIC '35201-3456789-3' / password 'Teacher@123' (SST -> HM Eligible)")
    print("  - Teacher 4:  CNIC '35201-4567890-4' / password 'Teacher@123' (Pending Verification)")
    print(f"Server starting on http://{host}:{port} (debug={debug})")
    print("=======================================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)
    app.run(host=host, port=port, debug=debug)
