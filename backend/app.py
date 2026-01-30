"""
Bhavya Health Data Fetcher - FastAPI Backend
Real-time progress updates via Server-Sent Events (SSE)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timedelta
import requests
import mysql.connector
from mysql.connector import Error
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

warnings.filterwarnings('ignore')
requests.packages.urllib3.disable_warnings()

# Load environment variables from .env file in parent directory
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
print(f"Loading .env from: {ENV_PATH}")
load_dotenv(dotenv_path=ENV_PATH)

# Debug: Print loaded config
print(f"DB_HOST from env: {os.getenv('DB_HOST')}")

app = FastAPI(title="Bhavya Health Data Fetcher API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend path
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
print(f"Frontend directory: {FRONTEND_DIR}")

# ============== CONFIGURATION FROM .env ==============
BASE_URL = os.getenv("API_BASE_URL", "https://bipard.bhavyabiharhealth.in/api/bhavya")
CREDENTIALS = {
    "secretKey": os.getenv("API_SECRET_KEY"),
    "clientKey": os.getenv("API_CLIENT_KEY")
}

MYSQL_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "test")
}

# Debug: Print MySQL config (without password)
print(f"MySQL Config: host={MYSQL_CONFIG['host']}, user={MYSQL_CONFIG['user']}, database={MYSQL_CONFIG['database']}")

# Table name - Change this if you want to use a different table
TABLE_NAME = "bhavya_realtime_health__report_data"

# All 34 Endpoints
ENDPOINTS = [
    {"name": "staff_data", "endpoint": "staff_data", "desc": "Staff/HR Data"},
    {"name": "unique_patients", "endpoint": "unique_patients", "desc": "Unique Patients"},
    {"name": "opd_patients", "endpoint": "opd_patients", "desc": "OPD Patients"},
    {"name": "male_female_count", "endpoint": "malefemaleCount", "desc": "Gender-wise Count"},
    {"name": "patient_journey_time", "endpoint": "patientJourneyTime", "desc": "Journey Time"},
    {"name": "patient_waiting_time", "endpoint": "patientWaitingTime", "desc": "Waiting Time"},
    {"name": "eaushadhi_facility_count", "endpoint": "eAushadhiFacilityCount", "desc": "E-Aushadhi Facilities"},
    {"name": "ipd_facility_ward_bed", "endpoint": "IPDFacilityWardBed", "desc": "IPD Ward/Bed"},
    {"name": "ipd_patient_admit", "endpoint": "IPDPatientAdmit", "desc": "IPD Admissions"},
    {"name": "mlc_count", "endpoint": "MLCCount", "desc": "MLC Cases"},
    {"name": "ae_opd_consultation", "endpoint": "getAEOPDConsultation", "desc": "A&E OPD"},
    {"name": "ae_observation_count", "endpoint": "getAEObservationCount", "desc": "A&E Observation"},
    {"name": "abdm_data", "endpoint": "getABDMData", "desc": "ABDM Data"},
    {"name": "total_district", "endpoint": "getTotalDistrict", "desc": "Total Districts"},
    {"name": "total_live_district", "endpoint": "getTotalLiveDistrict", "desc": "Live Districts"},
    {"name": "total_block", "endpoint": "getTotalBlock", "desc": "Total Blocks"},
    {"name": "total_live_block", "endpoint": "getTotalLiveBlock", "desc": "Live Blocks"},
    {"name": "hsc_count", "endpoint": "getHSCcount", "desc": "HSC Count"},
    {"name": "hsc_patient_registered", "endpoint": "getHSCPatientRegistered", "desc": "HSC Patients Registered"},
    {"name": "cho_anm_count", "endpoint": "getCHO_ANMCount", "desc": "CHO/ANM Count"},
    {"name": "hsc_patient_till_now", "endpoint": "getHSCPatientTillNow", "desc": "HSC Patients Till Now"},
    {"name": "patient_visits_count_hsc", "endpoint": "getPatientVisitsCountHSC", "desc": "HSC Patient Visits"},
    {"name": "state_dashboard_patient_count", "endpoint": "getStateDashboardPatientCount", "desc": "State Dashboard"},
    {"name": "citizen_portal_facility_count", "endpoint": "getCitizenPortalDistrictFacilityCount", "desc": "Citizen Portal"},
    {"name": "patient_first_registration_opd", "endpoint": "getPatientFirstRegistrationOPD", "desc": "First Registration OPD"},
    {"name": "facilitator_asha_count", "endpoint": "get_facilitator_and_asha_count", "desc": "Facilitator/ASHA"},
    {"name": "bcm_dcm_count", "endpoint": "get_bcm_and_dcm_count", "desc": "BCM/DCM Count"},
    {"name": "dist_block_village_panch_hsc", "endpoint": "get_dist_block_village_panch_hsc_count", "desc": "Geographic Data"},
    {"name": "asha_household", "endpoint": "getAshaHousehold", "desc": "ASHA Household"},
    {"name": "asha_beneficiary", "endpoint": "getAshaBeneficiary", "desc": "ASHA Beneficiary"},
    {"name": "asha_eligible_couple", "endpoint": "getAshaEligibleCouple", "desc": "Eligible Couples"},
    {"name": "asha_pregnant_women", "endpoint": "getAshaPregnant_Women", "desc": "Pregnant Women"},
    {"name": "total_child_care", "endpoint": "getTotalchildcare", "desc": "Child Care"},
    {"name": "delivery_count", "endpoint": "getDeliveryCount", "desc": "Delivery Count"},
]

TARGET_COLUMNS = [
    "data_date", "state_name", "focus_area", "year", "month",
    "number_of_abdm_cards_linked", "number_of_abdm_cards_shared", "number_of_abdm_cards_created",
    "number_of_abdm_health_facility_registry", "abdm_healthcare_professionals_registry",
    "number_of_doctors", "number_of_nurses", "number_of_data_entry_operators",
    "number_of_pharmacists", "number_of_lab_attendents", "number_of_community_health_officers",
    "number_of_auxiliary_nurse_midwives", "facilitator_count", "asha_count",
    "number_of_total_patients_visit", "number_of_patient_opd_patient_visit",
    "number_of_male_patient_visit", "number_of_female_patient_visit", "number_of_transgender_patient_visit",
    "unique_patients_total", "number_of_ipd_patient_admission", "number_of_ipd_patient_discharge",
    "number_of_ipd_patient_surgery", "number_of_ipd_patient_transfer",
    "medico_legal_cases_count", "accident_emergency_opd_count", "accident_emergency_observation_count",
    "total_district", "total_blocks", "total_villages", "total_panchayats", "total_hsc",
    "live_hsc", "live_facilities", "asha_beneficiary_count", "asha_eligible_couple_count",
    "asha_household_count", "asha_pregnant_women_count", "delivery_count", "total_child_care_count",
    "eaushadhi_facility_count", "patient_journey_time_min", "patient_waiting_time_min",
    "hsc_patient_registered_total", "hsc_patient_till_now_total", "state_dashboard_patient_count",
    "start_date", "end_date", "source", "citizen_portal_live_facility_count",
    "number_of_wards", "number_of_beds", "fetched_at"
]

def get_create_table_sql():
    """Generate CREATE TABLE SQL with the configured table name"""
    return f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        data_date VARCHAR(50) NOT NULL,
        state_name TEXT, focus_area TEXT, year TEXT, month TEXT,
        number_of_abdm_cards_linked TEXT, number_of_abdm_cards_shared TEXT,
        number_of_abdm_cards_created TEXT, number_of_abdm_health_facility_registry TEXT,
        abdm_healthcare_professionals_registry TEXT, number_of_doctors TEXT,
        number_of_nurses TEXT, number_of_data_entry_operators TEXT,
        number_of_pharmacists TEXT, number_of_lab_attendents TEXT,
        number_of_community_health_officers TEXT, number_of_auxiliary_nurse_midwives TEXT,
        facilitator_count TEXT, asha_count TEXT, number_of_total_patients_visit TEXT,
        number_of_patient_opd_patient_visit TEXT, number_of_male_patient_visit TEXT,
        number_of_female_patient_visit TEXT, number_of_transgender_patient_visit TEXT,
        unique_patients_total TEXT, number_of_ipd_patient_admission TEXT,
        number_of_ipd_patient_discharge TEXT, number_of_ipd_patient_surgery TEXT,
        number_of_ipd_patient_transfer TEXT, medico_legal_cases_count TEXT,
        accident_emergency_opd_count TEXT, accident_emergency_observation_count TEXT,
        total_district TEXT, total_blocks TEXT, total_villages TEXT,
        total_panchayats TEXT, total_hsc TEXT, live_hsc TEXT, live_facilities TEXT,
        asha_beneficiary_count TEXT, asha_eligible_couple_count TEXT,
        asha_household_count TEXT, asha_pregnant_women_count TEXT,
        delivery_count TEXT, total_child_care_count TEXT, eaushadhi_facility_count TEXT,
        patient_journey_time_min TEXT, patient_waiting_time_min TEXT,
        hsc_patient_registered_total TEXT, hsc_patient_till_now_total TEXT,
        state_dashboard_patient_count TEXT, start_date TEXT, end_date TEXT,
        source TEXT, citizen_portal_live_facility_count TEXT,
        number_of_wards TEXT, number_of_beds TEXT, fetched_at TEXT,
        UNIQUE KEY unique_date_idx (data_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """


class DateRangeRequest(BaseModel):
    from_date: str
    to_date: str


class DataFetcher:
    def __init__(self):
        self.session = None
        self.token = None
        self._create_session()

    def _create_session(self):
        self.session = requests.Session()
        retry = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get_token(self):
        try:
            resp = self.session.post(
                f"{BASE_URL}/generateToken",
                json=CREDENTIALS,
                headers={"Content-Type": "application/json"},
                timeout=30, verify=False
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict):
                    self.token = data.get("token") or data.get("access_token") or data.get("accessToken")
                elif isinstance(data, str):
                    self.token = data
                return self.token is not None
        except Exception as e:
            print(f"Token error: {e}")
        return False

    def fetch_endpoint(self, endpoint_path, start_date, end_date):
        if not self.token and not self.get_token():
            return None

        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        body = {"tdate": start_date, "dEndDate": end_date}

        try:
            resp = self.session.get(
                f"{BASE_URL}/{endpoint_path}",
                headers=headers, json=body, timeout=10, verify=False
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0] if isinstance(data[0], dict) else {"value": data[0]}
                if isinstance(data, dict):
                    for key in ["data", "result", "results", "records"]:
                        if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                            return data[key][0]
                    return data
            elif resp.status_code == 401:
                self.get_token()
        except:
            pass
        return None

    def safe_get(self, data, key, default="Not Available"):
        if data is None:
            return default
        val = data.get(key)
        if val is None or val == "" or str(val).lower() in ["null", "none", "nan", "not found", "notfound", "n/a", "na", "-"]:
            return default
        return str(val)

    def process_data(self, all_data, data_date, start_date, end_date):
        row = {col: "Not Available" for col in TARGET_COLUMNS}

        row["data_date"] = str(data_date)
        row["state_name"] = "Bihar"
        row["focus_area"] = "State Health System Performance"
        date_obj = datetime.strptime(data_date, "%Y-%m-%d")
        row["year"] = str(date_obj.year)
        row["month"] = date_obj.strftime("%B")
        row["start_date"] = str(start_date)
        row["end_date"] = str(end_date)
        row["source"] = "Bhavya"
        row["fetched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if all_data.get("staff_data"):
            d = all_data["staff_data"]
            row["number_of_doctors"] = self.safe_get(d, "doctor")
            row["number_of_nurses"] = self.safe_get(d, "nurse")
            row["number_of_data_entry_operators"] = self.safe_get(d, "deo")
            row["number_of_pharmacists"] = self.safe_get(d, "pharmacist")
            row["number_of_lab_attendents"] = self.safe_get(d, "lab_attendent")
            row["number_of_community_health_officers"] = self.safe_get(d, "cho_staff")

        if all_data.get("unique_patients"):
            row["unique_patients_total"] = self.safe_get(all_data["unique_patients"], "total_patient")

        if all_data.get("opd_patients"):
            row["number_of_patient_opd_patient_visit"] = self.safe_get(all_data["opd_patients"], "patient_visit")

        if all_data.get("male_female_count"):
            d = all_data["male_female_count"]
            row["number_of_male_patient_visit"] = self.safe_get(d, "male_patient_visist")
            row["number_of_female_patient_visit"] = self.safe_get(d, "female_patient_visist")
            row["number_of_transgender_patient_visit"] = self.safe_get(d, "transgender_patient_visits")

        if all_data.get("patient_journey_time"):
            row["patient_journey_time_min"] = self.safe_get(all_data["patient_journey_time"], "journey_time_min")

        if all_data.get("patient_waiting_time"):
            row["patient_waiting_time_min"] = self.safe_get(all_data["patient_waiting_time"], "waiting_time_min")

        if all_data.get("eaushadhi_facility_count"):
            row["eaushadhi_facility_count"] = self.safe_get(all_data["eaushadhi_facility_count"], "count")

        if all_data.get("ipd_facility_ward_bed"):
            d = all_data["ipd_facility_ward_bed"]
            row["number_of_wards"] = self.safe_get(d, "ward_count", self.safe_get(d, "wards"))
            row["number_of_beds"] = self.safe_get(d, "bed_count", self.safe_get(d, "beds"))

        if all_data.get("ipd_patient_admit"):
            d = all_data["ipd_patient_admit"]
            row["number_of_ipd_patient_admission"] = self.safe_get(d, "admission")
            row["number_of_ipd_patient_discharge"] = self.safe_get(d, "discharge")
            row["number_of_ipd_patient_surgery"] = self.safe_get(d, "surgery")
            row["number_of_ipd_patient_transfer"] = self.safe_get(d, "transfer")

        if all_data.get("mlc_count"):
            row["medico_legal_cases_count"] = self.safe_get(all_data["mlc_count"], "count")

        if all_data.get("ae_opd_consultation"):
            row["accident_emergency_opd_count"] = self.safe_get(all_data["ae_opd_consultation"], "count")

        if all_data.get("ae_observation_count"):
            row["accident_emergency_observation_count"] = self.safe_get(all_data["ae_observation_count"], "count")

        if all_data.get("abdm_data"):
            d = all_data["abdm_data"]
            row["number_of_abdm_cards_linked"] = self.safe_get(d, "Linked")
            row["number_of_abdm_cards_shared"] = self.safe_get(d, "Shared")
            row["number_of_abdm_cards_created"] = self.safe_get(d, "Created")
            row["number_of_abdm_health_facility_registry"] = self.safe_get(d, "HFR")
            row["abdm_healthcare_professionals_registry"] = self.safe_get(d, "HPR")

        if all_data.get("total_district"):
            row["total_district"] = self.safe_get(all_data["total_district"], "count")

        if all_data.get("total_block"):
            row["total_blocks"] = self.safe_get(all_data["total_block"], "count")

        if all_data.get("hsc_count"):
            d = all_data["hsc_count"]
            row["live_hsc"] = self.safe_get(d, "live_hsc")
            row["total_hsc"] = self.safe_get(d, "total_hsc")

        if all_data.get("hsc_patient_registered"):
            row["hsc_patient_registered_total"] = self.safe_get(all_data["hsc_patient_registered"], "total_patient")

        if all_data.get("cho_anm_count"):
            d = all_data["cho_anm_count"]
            anm = self.safe_get(d, "anm")
            if anm not in ["Not Available", "0", "0.0"]:
                row["number_of_auxiliary_nurse_midwives"] = anm

        if all_data.get("hsc_patient_till_now"):
            row["hsc_patient_till_now_total"] = self.safe_get(all_data["hsc_patient_till_now"], "total_patient")

        if all_data.get("patient_visits_count_hsc"):
            row["number_of_total_patients_visit"] = self.safe_get(all_data["patient_visits_count_hsc"], "pateint_visits")

        if all_data.get("state_dashboard_patient_count"):
            row["state_dashboard_patient_count"] = self.safe_get(all_data["state_dashboard_patient_count"], "patient_count")

        if all_data.get("citizen_portal_facility_count"):
            d = all_data["citizen_portal_facility_count"]
            row["citizen_portal_live_facility_count"] = self.safe_get(d, "Total_Live_Facilities")
            row["live_facilities"] = self.safe_get(d, "Total_Live_Facilities")

        if all_data.get("facilitator_asha_count"):
            d = all_data["facilitator_asha_count"]
            row["facilitator_count"] = self.safe_get(d, "facilitator_count")
            row["asha_count"] = self.safe_get(d, "asha_count")

        if all_data.get("dist_block_village_panch_hsc"):
            d = all_data["dist_block_village_panch_hsc"]
            row["total_villages"] = self.safe_get(d, "village_counts")
            row["total_panchayats"] = self.safe_get(d, "panchayat_counts")

        if all_data.get("asha_household"):
            row["asha_household_count"] = self.safe_get(all_data["asha_household"], "household_count")

        if all_data.get("asha_beneficiary"):
            row["asha_beneficiary_count"] = self.safe_get(all_data["asha_beneficiary"], "beneficiary_count")

        if all_data.get("asha_eligible_couple"):
            row["asha_eligible_couple_count"] = self.safe_get(all_data["asha_eligible_couple"], "ec_count")

        if all_data.get("asha_pregnant_women"):
            row["asha_pregnant_women_count"] = self.safe_get(all_data["asha_pregnant_women"], "pw_count")

        if all_data.get("total_child_care"):
            row["total_child_care_count"] = self.safe_get(all_data["total_child_care"], "child_count")

        if all_data.get("delivery_count"):
            row["delivery_count"] = self.safe_get(all_data["delivery_count"], "delivery_count")

        # Final sanitization - replace all invalid/missing values with "Not Available"
        for key in row:
            val = row[key]
            if val is None or val == "" or str(val).lower() in ["null", "none", "nan", "not found", "notfound", "n/a", "na", "-"]:
                row[key] = "Not Available"
            else:
                row[key] = str(val)

        return row


class DatabaseManager:
    @staticmethod
    def get_connection():
        try:
            print(f"Connecting to database: {MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}")
            conn = mysql.connector.connect(**MYSQL_CONFIG)
            conn.autocommit = False  # Explicit transaction control
            print("Database connected successfully")
            return conn
        except Error as e:
            print(f"DB Connection Error: {e}")
            return None

    @staticmethod
    def table_exists(conn):
        """Check if table exists"""
        try:
            cursor = conn.cursor()
            cursor.execute(f"SHOW TABLES LIKE '{TABLE_NAME}'")
            result = cursor.fetchone()
            cursor.close()
            exists = result is not None
            print(f"Table '{TABLE_NAME}' exists: {exists}")
            return exists
        except Exception as e:
            print(f"Table check error: {e}")
            return False

    @staticmethod
    def create_table(conn):
        """Create the table if it doesn't exist"""
        try:
            cursor = conn.cursor()
            print(f"Creating table {TABLE_NAME}...")

            # Execute CREATE TABLE
            create_sql = get_create_table_sql()
            cursor.execute(create_sql)
            conn.commit()
            cursor.close()

            # Verify table was created
            if DatabaseManager.table_exists(conn):
                print(f"Table {TABLE_NAME} created and verified successfully!")
                return True
            else:
                print(f"Table creation executed but verification failed!")
                return False
        except Error as e:
            print(f"Table creation error: {e}")
            try:
                conn.rollback()
            except:
                pass
            return False

    @staticmethod
    def ensure_table_exists(conn):
        """Check if table exists, create if not"""
        try:
            if DatabaseManager.table_exists(conn):
                print("Table already exists")
                return True
            else:
                print("Table does not exist, creating...")
                return DatabaseManager.create_table(conn)
        except Exception as e:
            print(f"ensure_table_exists error: {e}")
            # Try to create anyway
            return DatabaseManager.create_table(conn)

    @staticmethod
    def check_duplicate(conn, data_date):
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE data_date = %s", (data_date,))
            count = cursor.fetchone()[0]
            cursor.close()
            return count > 0
        except Error as e:
            print(f"Duplicate check error: {e}")
            return False

    @staticmethod
    def insert_data(conn, row_data):
        try:
            # Double check for duplicate before insert
            if DatabaseManager.check_duplicate(conn, row_data.get("data_date")):
                print(f"Duplicate found for {row_data.get('data_date')}, skipping")
                return False

            columns = ", ".join(row_data.keys())
            placeholders = ", ".join(["%s"] * len(row_data))
            # Use INSERT IGNORE to prevent duplicate key errors
            query = f"INSERT IGNORE INTO {TABLE_NAME} ({columns}) VALUES ({placeholders})"
            cursor = conn.cursor()
            cursor.execute(query, list(row_data.values()))
            conn.commit()
            affected = cursor.rowcount
            cursor.close()
            print(f"Insert result: {affected} row(s) affected")
            return affected > 0
        except Error as e:
            print(f"Insert error: {e}")
            try:
                conn.rollback()
            except:
                pass
            return False

    @staticmethod
    def get_record_count(conn):
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            result = cursor.fetchone()
            cursor.close()
            count = result[0] if result else 0
            print(f"get_record_count: {count}")
            return count
        except Exception as e:
            print(f"Record count error: {e}")
            return 0

    @staticmethod
    def get_existing_dates(conn):
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT data_date FROM {TABLE_NAME} ORDER BY data_date DESC LIMIT 50")
            dates = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return dates
        except Error as e:
            print(f"Get dates error: {e}")
            return []


# ============== API ENDPOINTS ==============

@app.get("/")
async def root():
    """Serve the frontend dashboard at root URL"""
    frontend_path = FRONTEND_DIR / "index.html"
    print(f"Looking for frontend at: {frontend_path}")
    print(f"Frontend exists: {frontend_path.exists()}")
    if frontend_path.exists():
        return FileResponse(frontend_path, media_type="text/html")
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "ok", "message": "Bhavya Health Data Fetcher API"}


@app.get("/api/status")
async def get_status():
    conn = DatabaseManager.get_connection()
    if not conn:
        return {"database": "disconnected", "table_exists": False, "record_count": 0, "recent_dates": []}

    try:
        # Check if table exists
        table_exists = DatabaseManager.table_exists(conn)
        print(f"Status check - table_exists: {table_exists}")

        if not table_exists:
            # Try to create table
            print("Table not found, attempting to create...")
            created = DatabaseManager.create_table(conn)
            if created:
                table_exists = True
                print("Table created successfully")
            else:
                print("Failed to create table")

        # Get record count and dates if table exists
        record_count = 0
        recent_dates = []
        if table_exists:
            record_count = DatabaseManager.get_record_count(conn)
            recent_dates = DatabaseManager.get_existing_dates(conn)[:10]
            print(f"Record count: {record_count}")

        conn.close()
        return {
            "database": "connected",
            "table_exists": table_exists,
            "record_count": record_count,
            "recent_dates": recent_dates
        }
    except Exception as e:
        print(f"Status check error: {e}")
        conn.close()
        return {"database": "connected", "table_exists": False, "record_count": 0, "recent_dates": [], "error": str(e)}


@app.get("/api/endpoints")
async def get_endpoints():
    return {"endpoints": ENDPOINTS, "total": len(ENDPOINTS)}


@app.get("/api/debug")
async def debug_status():
    """Debug endpoint to check database and table status"""
    result = {
        "config": {
            "host": MYSQL_CONFIG.get("host", "not set"),
            "database": MYSQL_CONFIG.get("database", "not set"),
            "user": MYSQL_CONFIG.get("user", "not set"),
            "table_name": TABLE_NAME
        },
        "connection": False,
        "table_check": None,
        "record_count": None,
        "errors": []
    }

    # Test connection
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        result["connection"] = True

        # Test table exists with SHOW TABLES
        try:
            cursor = conn.cursor()
            cursor.execute(f"SHOW TABLES LIKE '{TABLE_NAME}'")
            table_result = cursor.fetchone()
            result["table_check"] = "exists" if table_result else "not found"
            cursor.close()
        except Exception as e:
            result["errors"].append(f"Table check error: {str(e)}")

        # Test record count
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            count = cursor.fetchone()[0]
            result["record_count"] = count
            cursor.close()
        except Exception as e:
            result["errors"].append(f"Record count error: {str(e)}")

        conn.close()
    except Exception as e:
        result["errors"].append(f"Connection error: {str(e)}")

    return result


@app.post("/api/setup-table")
async def setup_table():
    """Manually create the database table if it doesn't exist"""
    conn = DatabaseManager.get_connection()
    if not conn:
        return {"success": False, "message": "Database connection failed"}

    table_existed = DatabaseManager.table_exists(conn)

    if table_existed:
        count = DatabaseManager.get_record_count(conn)
        conn.close()
        return {
            "success": True,
            "message": "Table already exists",
            "table_created": False,
            "record_count": count
        }

    created = DatabaseManager.create_table(conn)
    conn.close()

    if created:
        return {
            "success": True,
            "message": "Table created successfully",
            "table_created": True,
            "record_count": 0
        }
    return {"success": False, "message": "Failed to create table"}


@app.get("/api/fetch/today")
async def fetch_today():
    today = datetime.now().strftime("%Y-%m-%d")
    return StreamingResponse(
        fetch_data_stream([today]),
        media_type="text/event-stream"
    )


@app.post("/api/fetch/range")
async def fetch_range(request: DateRangeRequest):
    try:
        from_dt = datetime.strptime(request.from_date, "%Y-%m-%d")
        to_dt = datetime.strptime(request.to_date, "%Y-%m-%d")

        if from_dt > to_dt:
            raise HTTPException(400, "From date cannot be after To date")

        dates = []
        current = from_dt
        while current <= to_dt:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        return StreamingResponse(
            fetch_data_stream(dates),
            media_type="text/event-stream"
        )
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")


async def fetch_data_stream(dates):
    """Generator for SSE streaming with concurrent API calls"""
    fetcher = DataFetcher()
    conn = DatabaseManager.get_connection()

    if not conn:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Database connection failed'})}\n\n"
        return

    # Ensure table exists before proceeding
    yield f"data: {json.dumps({'type': 'log', 'message': 'Checking database table...'})}\n\n"
    await asyncio.sleep(0.1)

    if not DatabaseManager.ensure_table_exists(conn):
        yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to create database table'})}\n\n"
        conn.close()
        return

    yield f"data: {json.dumps({'type': 'log', 'message': 'Database table ready'})}\n\n"
    await asyncio.sleep(0.1)

    # Send start event
    yield f"data: {json.dumps({'type': 'start', 'total_dates': len(dates), 'total_endpoints': len(ENDPOINTS)})}\n\n"
    await asyncio.sleep(0.1)

    # Get token
    yield f"data: {json.dumps({'type': 'log', 'message': 'Getting API token...'})}\n\n"
    if not fetcher.get_token():
        yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to get API token'})}\n\n"
        return
    yield f"data: {json.dumps({'type': 'log', 'message': 'Token obtained successfully'})}\n\n"
    await asyncio.sleep(0.1)

    success_count = 0
    skip_count = 0
    fail_count = 0

    # Create ThreadPoolExecutor for concurrent API calls
    executor = ThreadPoolExecutor(max_workers=34)  # One worker per endpoint for maximum parallelism

    for date_idx, data_date in enumerate(dates):
        yield f"data: {json.dumps({'type': 'date_start', 'date': data_date, 'date_index': date_idx + 1, 'total_dates': len(dates)})}\n\n"
        await asyncio.sleep(0.1)

        # Check duplicate before fetching
        if DatabaseManager.check_duplicate(conn, data_date):
            yield f"data: {json.dumps({'type': 'date_skip', 'date': data_date, 'reason': 'Already exists in database'})}\n\n"
            skip_count += 1
            continue

        # Notify that we're fetching all endpoints concurrently
        yield f"data: {json.dumps({'type': 'log', 'message': f'Fetching all 34 endpoints concurrently for {data_date}...'})}\n\n"
        await asyncio.sleep(0.1)

        # Send endpoint_start for all endpoints at once
        for ep_idx, ep in enumerate(ENDPOINTS):
            yield f"data: {json.dumps({'type': 'endpoint_start', 'endpoint': ep['name'], 'desc': ep['desc'], 'index': ep_idx + 1, 'total': len(ENDPOINTS)})}\n\n"
        await asyncio.sleep(0.05)

        # Fetch all endpoints concurrently using ThreadPoolExecutor
        loop = asyncio.get_event_loop()

        async def fetch_single_endpoint(ep):
            """Fetch a single endpoint asynchronously using executor"""
            data = await loop.run_in_executor(
                executor,
                fetcher.fetch_endpoint,
                ep["endpoint"],
                data_date,
                data_date
            )
            return ep["name"], data

        # Create tasks for all endpoints
        tasks = [fetch_single_endpoint(ep) for ep in ENDPOINTS]

        # Execute all tasks concurrently and wait for all to complete
        results = await asyncio.gather(*tasks)

        # Process results
        all_data = {}
        for ep_name, data in results:
            all_data[ep_name] = data
            status = "success" if data else "no_data"
            yield f"data: {json.dumps({'type': 'endpoint_done', 'endpoint': ep_name, 'status': status, 'data': data is not None})}\n\n"

        await asyncio.sleep(0.05)

        # Refresh token for next iteration if there are more dates
        if date_idx < len(dates) - 1:
            fetcher.get_token()

        # Process and save
        yield f"data: {json.dumps({'type': 'log', 'message': f'Processing data for {data_date}...'})}\n\n"
        row_data = fetcher.process_data(all_data, data_date, data_date, data_date)

        if DatabaseManager.insert_data(conn, row_data):
            yield f"data: {json.dumps({'type': 'date_done', 'date': data_date, 'status': 'success', 'message': 'Data saved to database'})}\n\n"
            success_count += 1
        else:
            yield f"data: {json.dumps({'type': 'date_done', 'date': data_date, 'status': 'failed', 'message': 'Failed to save to database'})}\n\n"
            fail_count += 1

        await asyncio.sleep(0.1)

    # Cleanup executor
    executor.shutdown(wait=False)

    # Send completion
    total_records = DatabaseManager.get_record_count(conn)
    conn.close()

    yield f"data: {json.dumps({'type': 'complete', 'success': success_count, 'skipped': skip_count, 'failed': fail_count, 'total_records': total_records})}\n\n"


# ============== MOUNT STATIC FILES ==============
# Mount frontend folder for any static assets (CSS, JS, images if added later)
# This must be after all API routes to avoid conflicts
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    print(f"Static files mounted from: {FRONTEND_DIR}")


if __name__ == "__main__":
    import uvicorn
    # Use PORT from environment (for Render) or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
