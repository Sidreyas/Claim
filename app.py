
from flask import Flask, request, jsonify, send_file
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import openai
from flask_cors import CORS
import json
import os
from werkzeug.utils import secure_filename
import re
from vision_compare import (init_embedders, generate_embedding, generate_image_embedding,
                          create_or_load_indices, create_empty_indices, add_record, save_indices)
from datetime import datetime
import uuid
import base64
import mimetypes
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

#logging.basicConfig(level=logging.DEBUG)
#logger = logging.getLogger(__name__)

# Configure image upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
# Configure image upload settings
UPLOAD_FOLDER = 'uploaded_images'
ALLOWED_MIME_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'application/pdf': '.pdf',
    'image/jpg': '.jpg'
}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
cors_origins = os.environ.get('CORS_ORIGINS', '*')
CORS(app, origins=cors_origins.split(','))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

# Create the model
generation_config = {
    "temperature": 0.1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 20000,
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=generation_config,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_ocr_session = None

def _get_ocr_session():
    """Lazy-initialize the OCR few-shot session on first use."""
    global _ocr_session
    if _ocr_session is not None:
        return _ocr_session

    print("[OCR] Initializing few-shot session (uploading sample images to Gemini)...")
    files = [
        upload_to_gemini(os.path.join(BASE_DIR, "uploaded_images", "20250213_032806_25143ccc.jpg")),
        upload_to_gemini(os.path.join(BASE_DIR, "uploaded_images", "20250213_141405_e502f390.jpg")),
        upload_to_gemini(os.path.join(BASE_DIR, "uploaded_images", "20250213_151912_2bfbd617.jpeg")),
    ]

    _ocr_session = model.start_chat(
    history=[
        {
            "role": "user",
            "parts": [
                "Extract the following key fields from the OCR output of a hospital discharge note: Hospital Name, Name, Age, Sex, Ward, MRN, RN, IC or NRIC(it is a 12 digit value sometimes with - and sometimes without), Date of Admission, Date of Discharge, Diagnosis (Include the complete diagnosis), Follow up Notes (May also be named 'Summary'), Name of Medical Officer (If no doctor name or medical officer name is found, leave this field empty), and Document Date. If a field is not found, return ''. Return the extracted data in compact, single-line JSON format, without any extra whitespace or line breaks. {\"Hospital Name\":\"SABAH WOMENAND CHILDREN HOSPITAL\",\"Name\":\"JASPREET KAUR\",\"Age\":\"28\",\"Sex\":\"FEMALE\",\"Ward\":\"33\",\"MRN\":\"null\",\"RN\":\"\",\"IC or NRIC\":\"960707-14-6352\",\"Date of Admission\":\"12/12/2024\",\"Date of Discharge\":\"16/12/2024\",\"Diagnosis\":\"Brain biopsy confirmed glioblastoma multiforme.\",\"Follow up Notes\":\"This patient received a six weeks course or radiation and will start a phase 2 clinical chemotherapy trial at the NIH. He was also started on seizure prophylaxis and pain medication.\",\"Name of Medical Officer\":\"ALMAN ISHAK\",\"Document Date\":\"12/12/2024\"}",
            ],
        },
        {
            "role": "model",
            "parts": [
                "```json\n[{\"Hospital Name\":\"SABAH WOMENAND CHILDREN HOSPITAL\",\"Name\":\"JASPREET KAUR\",\"Age\":\"28\",\"Sex\":\"FEMALE\",\"Ward\":\"33\",\"MRN\":\"\",\"RN\":\"\",\"IC or NRIC\":\"960707-14-6352\",\"Date of Admission\":\"12/12/2024\",\"Date of Discharge\":\"16/12/2024\",\"Diagnosis\":\"Brain biopsy confirmed glioblastoma multiforme.\",\"Follow up Notes\":\"This patient received a six weeks course or radiation and will start a phase 2 clinical chemotherapy trial at the NIH. He was also started on seizure prophylaxis and pain medication.\",\"Name of Medical Officer\":\"ALMAN ISHAK\",\"Document Date\":\"12/12/2024\"}]\n```",
            ],
        },
        {
            "role": "user",
            "parts": [
                files[0],
            ],
        },
        {
            "role": "model",
            "parts": [
                "```json\n[{\"Hospital Name\":\"SARAWAK GENERAL HOSPITAL\",\"Name\":\"CAROLINE AMPAK ANAK BETIE\",\"Age\":\"33\",\"Sex\":\"Female\",\"Ward\":\"GYNAE WARD\",\"MRN\":\"\",\"RN\":\"2024/048182\",\"IC or NRIC\":\"910716135596\",\"Date of Admission\":\"2/12/2024\",\"Date of Discharge\":\"5/12/2024\",\"Diagnosis\":\"Choriocarcinoma FIGO Stage 3, Score 9\",\"Follow up Notes\":\"Known case of 1. chronic hypertension on T. Perindopril 8mg ON, T. Metoprolol 50mg BD. 2. Choriocarcinoma with FIGO stage 3, score 7 -underwent S+C on 30/9/24 at Hospital Sri Aman -HPE (30/9/24): Gestational trophoblastic neoplasm in favor of choriocarcinoma. -CXR for reporting (27/9/24): right lower zone lung nodule suspicious of metastases -CT TAP (15/10/2024) shows: 1. Uterine mass in keeping with primary tumour 2. Lung metastases 3. Cholelithiasis BHCG trend: 25/9/2024 (pre S&C): 244577 30/9/2024 (post S&C): 143252 7/10/2024: 138870 15/10/2024: 157804 28/10/2024:9388 12/11/2024: 1991 26/11/2024: 2791 29/11/2024:3435 2/12/2024: 1293 -Started on EMA regime (100% full dose) on 27/11/24 and has completed two days of EMA regime with folinic acid given\",\"Name of Medical Officer\":\"\",\"Document Date\":\"\"}]\n```",
            ],
        },
        {
            "role": "user",
            "parts": [
            files[1],
            ],
        },
        {
            "role": "model",
            "parts": [
            "```json\n{\"Hospital Name\":\"KUALA PENYU\",\"Name\":\"SAM\",\"Age\":\"32 yrs\",\"Sex\":\"M\",\"Ward\":\"2 sw\",\"MRN\":\"\",\"RN\":\"9962\",\"IC or NRIC\":\"123456789\",\"Date of Admission\":\"4/5/2023\",\"Date of Discharge\":\"18/5/2023\",\"Diagnosis\":\"fluid wold 2° nephrotic syndrome.\",\"Follow up Notes\":\"my\\n(1) allow (1)\\n(2) with\\npo show k 600mg 1-1/2\\npo celia hourly us.\\npo calcium lactate hourly us.\\npo protopressure hourly us.\\npo femwel fumavate hourly us.\",\"Name of Medical Officer\":\"Dr. NURUL SYAFIQAH BINTI NORIZAN\",\"Document Date\":\"(1)3/23\"}\n```",
            ],
        },
        {
            "role": "user",
            "parts": [
            "in this one Document Date is \"18/5/23\"",
            ],
            },
        {
            "role": "model",
            "parts": [
            "```json\n{\"Hospital Name\":\"KUALA PENYU\",\"Name\":\"SAM\",\"Age\":\"32 yrs\",\"Sex\":\"M\",\"Ward\":\"2 sw\",\"MRN\":\"\",\"RN\":\"9962\",\"IC or NRIC\":\"123456789\",\"Date of Admission\":\"4/5/2023\",\"Date of Discharge\":\"18/5/2023\",\"Diagnosis\":\"fluid wold 2° nephrotic syndrome.\",\"Follow up Notes\":\"my\\n(1) allow (1)\\n(2) with\\npo show k 600mg 1-1/2\\npo celia hourly us.\\npo calcium lactate hourly us.\\npo protopressure hourly us.\\npo femwel fumavate hourly us.\",\"Name of Medical Officer\":\"Dr. NURUL SYAFIQAH BINTI NORIZAN\",\"Document Date\":\"18/5/23\"}\n```",
            ],
        },
        {
            "role": "user",
            "parts": [
            files[2],
            ],
        },
        {
            "role": "model",
            "parts": [
            "```json\n{\"Hospital Name\":\"HOSPITAL QUEEN ELIZABETH II\",\"Name\":\"Amirah\",\"Age\":\"31 y/o\",\"Sex\":\"FEMALE\",\"Ward\":\"icu\",\"MRN\":\"\",\"RN\":\"202448\",\"IC or NRIC\":\"987654321\",\"Date of Admission\":\"06/11/2022\",\"Date of Discharge\":\"20/11/2022\",\"Diagnosis\":\"MYO CARDIAL INFARCTION WITH ISCHEMIC HEART\",\"Follow up Notes\":\"1. ALLOW DISCHARGE\\n2. DISCHARGE WITH SC FONDAPARINUX 2.5MG OD 40\\n- T. PALVIX 75MG OD\\n- T. ASPIRIN 150MG OD\\n- T. PERINDOPRIL 8MG ON\\n2. FOR HIGH RISK NOTIFICATION\",\"Name of Medical Officer\":\"DR. BETTY DINSI\",\"Document Date\":\"20/11/2022\"}\n```",
            ],
        },
        {
            "role": "user",
            "parts": [
            "Doctor name is DR. KETTY DINSI you made the mistake because of the signature overlap",
        ],
        },
        {
        "role": "model",
        "parts": [
        "```json\n{\"Hospital Name\":\"HOSPITAL QUEEN ELIZABETH II\",\"Name\":\"Amirah\",\"Age\":\"31 y/o\",\"Sex\":\"FEMALE\",\"Ward\":\"icu\",\"MRN\":\"\",\"RN\":\"202448\",\"IC or NRIC\":\"987654321\",\"Date of Admission\":\"06/11/2022\",\"Date of Discharge\":\"20/11/2022\",\"Diagnosis\":\"MYO CARDIAL INFARCTION WITH ISCHEMIC HEART\",\"Follow up Notes\":\"1. ALLOW DISCHARGE\\n2. DISCHARGE WITH SC FONDAPARINUX 2.5MG OD 40\\n- T. PALVIX 75MG OD\\n- T. ASPIRIN 150MG OD\\n- T. PERINDOPRIL 8MG ON\\n2. FOR HIGH RISK NOTIFICATION\",\"Name of Medical Officer\":\"DR. KETTY DINSI\",\"Document Date\":\"20/11/2022\"}\n```",
        ],
        }
    ]
    )
    print("[OCR] Few-shot session ready.")
    return _ocr_session


def get_file_extension(content_type):
    """Get file extension from content type"""
    return ALLOWED_MIME_TYPES.get(content_type.lower())

def save_base64_file(base64_data, content_type):
    """
    Save base64 encoded file and return the saved file path
    """
    try:
        # Get file extension from content type
        file_extension = get_file_extension(content_type)
        if not file_extension:
            raise ValueError(f"Unsupported content type: {content_type}")

        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}{file_extension}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Decode and save the file
        file_data = base64.b64decode(base64_data)
        with open(filepath, 'wb') as f:
            f.write(file_data)

        return {
            'filename': filename,
            'filepath': filepath,
            'content_type': content_type
        }

    except Exception as e:
        raise Exception(f"Error saving file: {str(e)}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_filename(original_filename):
    """Generate a unique filename with timestamp and UUID"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    ext = original_filename.rsplit('.', 1)[1].lower()
    return f"{timestamp}_{unique_id}.{ext}"

openai.api_key = os.getenv('AZURE_OPENAI_API_KEY')
openai.api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
openai.api_type = 'azure'
openai.api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2023-03-15-preview')

# FAISS files always live next to app.py (not process cwd — avoids wrong folder / failed delete + reload bug)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
FAISS_TEXT_PATH = os.path.join(APP_ROOT, 'text_index.faiss')
FAISS_IMAGE_PATH = os.path.join(APP_ROOT, 'image_index.faiss')
FAISS_RECORDS_PATH = os.path.join(APP_ROOT, 'records.pkl')

# Initialize image embedder globally
image_embedder, _ = init_embedders()

# Load FAISS indices
text_index, image_index, records = create_or_load_indices(
    FAISS_TEXT_PATH, FAISS_IMAGE_PATH, FAISS_RECORDS_PATH,
)
print(f"FAISS paths: text={FAISS_TEXT_PATH} (ntotal={text_index.ntotal})")

# Function to generate embedding
def generate_embedding(text):
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    embedding = response.data[0].embedding
    return np.array(embedding)

def gemini_fraud_analysis(new_claim, matching_record):
    # Create the model
    generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 20000,
    "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=generation_config,
    )

    chat_session = model.start_chat(
    history=[
        {
        "role": "user",
        "parts": [
            "You are an expert in insurance fraud detection. Compare the following two claims:                                \n\n    New Claim:\n    - IC: 961206-14-5617\n    - Patient Name: SYAFIQ\n    - Diagnosis: Frontonasal Encephalo\n    - Doctor: AMIRUL\n    - Hospital: SABAH WOMENAND CHILDREN HOSPITAL\n    - Notes for Follow-up: Surgical reduction of the tissue, with placement of a dural patch over the defect )\n\n    Matching Record:\n    - IC: 961206-14-5617\n    - Patient Name: SYAFIQ\n    - Diagnosis: Frontonasal Encephalocele\n    - Doctor: AMIRUL\n    - Hospital: SABAH WOMENAND CHILDREN HOSPITAL\n    - Notes for Follow-up: Surgical reduction of the tissue, with placement of a dural patch over the defect (it is not exce)\n\n    Identify potential fraud indicators and explain your reasoning. Highlight any suspicious similarities or anomalies in a structured json format as below \n\n{\n\"Summary\": \"\",\n\"Fraud Indicators\": [\"\",\"\"],\n\"Analysis Result\": \"\",\n\"Patient Information\": \"\",\n\"Diagnosis\": \"\", \n\"Doctor and Hospital\": \"\",\n\"Treatment Details\": \"\",\n\"Typographical Errors\": \"\"\n,\n\"Conclusion\": \"\"\n}",
        ],
        },
        {
        "role": "model",
        "parts": [
            "```json\n{\n  \"Summary\": \"The two claims are highly similar, sharing identical patient information, diagnosis, doctor, hospital, and nearly identical treatment details. This raises a potential concern for duplicate billing or an attempt to claim for services already provided.\",\n  \"Fraud Indicators\": [\n    \"High Similarity Between Claims: Almost all fields are identical, suggesting potential duplication.\",\n    \"Slight Discrepancy in Notes: The minor difference in the 'Notes for Follow-up' section ('it is not exce') might indicate an attempt to differentiate the claims while describing the same procedure.\"\n  ],\n  \"Analysis Result\": \"The claims require further investigation. The identical patient details, diagnosis, doctor, and hospital are highly suspicious. The slight variation in the notes is not substantial enough to dismiss the possibility of fraud. Confirmation of service delivery for both claims is necessary.\",\n  \"Patient Information\": \"IC and Patient Name are identical across both claims, which is expected if it's the same patient. However, this strengthens the need to verify if two separate incidents/treatments occurred.\",\n  \"Diagnosis\": \"The diagnoses are very similar. 'Frontonasal Encephalo' vs 'Frontonasal Encephalocele'. They likely refer to the same condition. It is possible that the first diagnosis is a shorthand version. This is a point of concern as it could suggest attempts to bill multiple times for treatment of the same condition.\",\n  \"Doctor and Hospital\": \"The Doctor and Hospital are identical, suggesting the claims originate from the same source. This further reinforces the need to verify the legitimacy of both claims.\",\n  \"Treatment Details\": \"The treatment details described in 'Notes for Follow-up' are nearly identical, describing the same surgical procedure. The minor discrepancy ('it is not exce') may be an attempt to make the claims appear distinct while describing the same service.\",\n  \"Typographical Errors\": \"The matching record contains a typo ('exce' likely intended to be 'excessive' or similar). While not directly indicative of fraud, it highlights a lack of attention to detail, which could be present in fraudulent claims as well.\"\n}\n```",
        ],
        },
    ]
    )

    t = f"""New Claim:
        - IC: {new_claim['IC']}
        - Patient Name: {new_claim['Patient_Name']}
        - Diagnosis: {new_claim['Diagnosis']}
        - Doctor: {new_claim['Doctor']}
        - Hospital: {new_claim['Hospital']}
        - Notes for Follow-up: {new_claim['Notes_for_Follow_up']}

        Matching Record:
        - IC: {matching_record['IC']}
        - Patient Name: {matching_record['Name']}
        - Diagnosis: {matching_record['Diagnosis']}
        - Doctor: {matching_record['Doctor']}
        - Hospital: {matching_record['Hospital']}
        - Notes for Follow-up: {matching_record['Notes_for_Follow_up']}

        Identify potential fraud indicators and explain your reasoning. Highlight any suspicious similarities or anomalies.
        Provide a structured JSON response and incorperate the details inside the explanations"""

    response = chat_session.send_message(t)

    print(response.text)
    r = json.loads(response.text)
    return r
# GPT-based contextual analysis
def gpt_fraud_analysis(new_claim, matching_record):

    prompt = f"""
    You are an expert in insurance fraud detection. Compare the following two claims:

    New Claim:
    - IC: {new_claim['IC']}
    - Patient Name: {new_claim['Patient_Name']}
    - Diagnosis: {new_claim['Diagnosis']}
    - Doctor: {new_claim['Doctor']}
    - Hospital: {new_claim['Hospital']}
    - Notes for Follow-up: {new_claim['Notes_for_Follow_up']}

    Matching Record:
    - IC: {matching_record['IC']}
    - Patient Name: {matching_record['Name']}
    - Diagnosis: {matching_record['Diagnosis']}
    - Doctor: {matching_record['Doctor']}
    - Hospital: {matching_record['Hospital']}
    - Notes for Follow-up: {matching_record['Notes_for_Follow_up']}

    Identify potential fraud indicators and explain your reasoning. Highlight any suspicious similarities or anomalies.
    Provide a structured JSON response in the following format Example:
    {{
  "Summary": "Comparison of two medical claims for the same patient, SYAFIQ, with a diagnosis related to Frontonasal Encephalocele, treated by the same doctor, AMIRUL, at the same hospital, SABAH WOMEN AND CHILDREN HOSPITAL. The claims are largely similar but contain minor discrepancies in the diagnosis description and the notes for follow-up.",

  "Fraud Indicators": [
    "Inconsistency in Diagnosis Description: The diagnosis in the new claim is listed as 'Frontonasal Encephalo' which might be a typographical error or an intentional shortening of the actual diagnosis 'Frontonasal Encephalocele' found in the matching record.",
    "Incomplete Notes for Follow-up: The new claim's follow-up notes are identical to the matching record but are abruptly cut off without finishing the sentence, suggesting potential manipulation or error in data entry."
  ],

  "Analysis Result": {{
    "Patient Information": "IC: 961206-14-5617. Name: SYAFIQ. Discrepancies: None.",

    "Diagnosis": "New Claim: 'Frontonasal Encephalo'. Matching Record: 'Frontonasal Encephalocele'. Discrepancy: Minor discrepancy in the term used, which could be a typographical error.",

    "Doctor and Hospital": "Doctor: AMIRUL. Hospital: SABAH WOMEN AND CHILDREN HOSPITAL. Discrepancies: None.",

    "Treatment Details": "New Claim: 'Surgical reduction of the tissue, with placement of a dural patch over the defect'. Matching Record: 'Surgical reduction of the tissue, with placement of a dural patch over the defect (it is not exce)'. Discrepancy: Possible truncation in the follow-up notes.",

    "Typographical Errors": "The diagnosis 'Frontonasal Encephalo' appears to be an incomplete version of 'Frontonasal Encephalocele'. The follow-up notes in the new claim seem truncated compared to the matching record, potentially due to data entry errors or manipulation."
  }},

  "Conclusion": "The primary concerns are the slight variation in the diagnosis term and the incomplete follow-up notes in the new claim. These could be innocent typographical errors or data entry issues. However, in the context of insurance claims, even small discrepancies need thorough verification to rule out any attempt at fraud, such as attempting to file multiple claims for slightly different diagnoses or altering treatment details to claim higher insurance payouts. It is recommended to verify the accuracy of the diagnosis and completeness of the documentation with the healthcare provider before processing the claim."
}}"""
    print(prompt)
    response = openai.chat.completions.create(
    model="gpt-4",  # Your Azure OpenAI deployment name
    messages=[
        {"role": "system", "content": "You are an expert in insurance fraud detection. Always return a structured JSON response."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=500,
    temperature=0.2)
    r = response.choices[0].message.content
    try:
        return json.loads(r)
    except json.JSONDecodeError:
        print("Error decoding JSON:", r)
        return r

# Fraud Detection function

def convert_numpy_to_json_serializable(obj):
    """Convert numpy arrays to lists for JSON serialization"""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_json_serializable(item) for item in list]
    return obj

# Modify the detect_fraud function (indices passed explicitly — never rely on stale globals)
def detect_fraud(new_claim, text_index, image_index, records, k=10, text_threshold=0.85, image_threshold=0.85):
    fraud_cases = []
    print(f"\nAnalyzing new claim for IC: {new_claim['IC']}")

    if text_index.ntotal == 0 or len(records) == 0:
        print("FAISS text index is empty — no historical records to compare against.")
        return fraud_cases

    # Generate text embedding for new claim
    text_input = f"""
    IC: {new_claim['IC']}
    Doctor: {new_claim['Doctor']}
    Diagnosis: {new_claim['Diagnosis']}
    Hospital: {new_claim['Hospital']}
    Notes: {new_claim['Notes_for_Follow_up']}
    """
    new_text_embedding = generate_embedding(text_input).astype('float32').reshape(1, -1)

    # Generate image embedding if image is provided
    if 'Image_Path' in new_claim:
        new_image_embedding = generate_image_embedding(new_claim['Image_Path'], image_embedder).astype('float32').reshape(1, -1)

    # Search similar text embeddings
    text_distances, text_indices = text_index.search(new_text_embedding, k)
    print(f"Found {len(text_indices[0])} potential matches")

    for i, idx in enumerate(text_indices[0]):
        if idx == -1:  # FAISS returns -1 for empty slots
            continue

        record = records[idx]
        text_similarity = float(1 - (text_distances[0][i] / 2))
        print(f"\nChecking record {idx}:")
        print(f"Text similarity: {text_similarity*100:.2f}%")
        print(f"Comparing ICs: New={new_claim['IC']}, Existing={record['IC']}")

        is_suspicious = False
        fraud_type = []
        image_similarity = None

        # Case 1: Same patient, similar claim within 30 days
        if new_claim['IC'] == record['IC']:
            date_diff = abs(
                (pd.to_datetime(new_claim['Date_Admission'], dayfirst=True) -
                 pd.to_datetime(record['Date_Admission'], dayfirst=True)).days
            )
            print(f"Same patient, date difference: {date_diff} days")
            if date_diff < 30 or text_similarity > text_threshold:
                is_suspicious = True
                fraud_type.append(f"Duplicate claim within {date_diff} days")

        # Case 2: Different patient, very similar claim
        elif text_similarity > text_threshold:
            is_suspicious = True
            fraud_type.append(f"Similar claim from different patient (Text similarity: {text_similarity*100:.2f}%)")

        # Case 3: Check image similarity if text is suspicious
        if is_suspicious and 'Image_Path' in new_claim:
            image_distances, _ = image_index.search(new_image_embedding, 1)
            image_similarity = float(1 - (image_distances[0][0] / 2))
            print(f"Image similarity: {image_similarity*100:.2f}%")

            if image_similarity > image_threshold:
                fraud_type.append(f"Similar images detected ({image_similarity*100:.2f}%)")

        # If suspicious, perform detailed analysis
        if is_suspicious:
            print("[WARNING] Suspicious claim detected!")
            gpt_analysis = gemini_fraud_analysis(new_claim, record)

            # Create a clean version of the record without embeddings
            clean_record = {
                'IC': record['IC'],
                'Name': record['Name'],
                'Age': record['Age'],
                'Doctor': record['Doctor'],
                'Specialty': record['Specialty'],
                'Hospital': record['Hospital'],
                'Date_Admission': record['Date_Admission'],
                'Date_Discharge': record['Date_Discharge'],
                'Diagnosis': record['Diagnosis'],
                'Notes_for_Follow_up': record['Notes_for_Follow_up'],
                'Image_Path': record['Image_Path']
            }

            fraud_cases.append({
                'Matched_IC': record['IC'],
                'Text_Similarity': text_similarity,
                'Image_Similarity': image_similarity,
                'Fraud_Types': fraud_type,
                'Analysis': gpt_analysis,
                'Matching_Record': clean_record
            })

    print(f"\nFound {len(fraud_cases)} suspicious cases")
    return fraud_cases

# Add this list of exclusion words after the base_records initialization
EXCLUSION_WORDS = [
    'Suicide', 'War', 'Crime', 'Criminal', 'Terrorist', 'Strike', 'Riot', 'Assault',
    'Quarrel', 'Stab', 'Alcohol', 'Drug', 'Intoxication', 'Pregnancy', 'Child birth',
    'Persistent trophoblastic disease', 'Gestational', 'Choriocarcinoma', 'Hyaditiform mole',
    'Invasive mole', 'Mole', 'Fetal', 'Singleton', 'Delivery', 'Prenatal', 'Postnatal',
    'SVD', 'VBAC', 'Gynae', 'Obsterics', 'Gynaecology', 'Miscarriage', 'Abortion',
    'Contraceptive', 'Infertility', 'Erectile', 'Impotence', 'Sterilization'
]

def validate_claim_data(form_data, ocr_data):
    """Validate the claim by comparing form data against OCR data"""
    validation_results = {
        'is_valid': True,
        'errors': [],
        'updates': {},
        'warnings': []
    }

    if form_data.get('Diagnosis', '').lower() != ocr_data.get('Diagnosis', '').lower():
        validation_results['updates']['Diagnosis'] = ocr_data.get('Diagnosis')
        validation_results['warnings'].append('Diagnosis updated to match discharge note')

    if form_data.get('Age', '').lower() != ocr_data.get('Age', '').lower():
        validation_results['updates']['Age'] = ocr_data.get('Age')
        validation_results['warnings'].append('Age updated to match discharge note')

    if form_data.get('Doctor', '').lower() != ocr_data.get('Doctor', '').lower():
        validation_results['updates']['Doctor'] = ocr_data.get('Doctor')
        validation_results['warnings'].append('Doctor updated to match discharge note')

    # Validate and update Notes_for_Follow_up
    if form_data.get('Notes_for_Follow_up', '').lower() != ocr_data.get('Notes_for_Follow_up', '').lower():
        validation_results['updates']['Notes_for_Follow_up'] = ocr_data.get('Notes_for_Follow_up')
        validation_results['warnings'].append('Follow-up notes updated to match discharge note')


    # Check for discharge note
    if not ocr_data.get('Notes_for_Follow_up', '').strip():
        validation_results['is_valid'] = False
        validation_results['errors'].append('Incomplete submission: Discharge Note not provided')
        return validation_results

    form_ic = re.sub(r'[-/]', '', form_data.get('IC', ''))
    ocr_ic = re.sub(r'[-/]', '', ocr_data.get('IC', ''))

    # Validate Name and NRIC match
    if form_data.get('Patient_Name', '').lower() != ocr_data.get('Patient_Name', '').lower() or \
       form_ic != ocr_ic:
        validation_results['is_valid'] = False
        validation_results['errors'].append('Name or IC in form does not match with discharge note')
        return validation_results

    # Validate Hospital Name
    if form_data.get('Hospital', '').lower() != ocr_data.get('Hospital', '').lower():
        validation_results['updates']['Hospital'] = ocr_data.get('Hospital')
        validation_results['warnings'].append('Hospital name in form updated to match discharge note')

    # Validate Admission Date
    form_admission = pd.to_datetime(form_data.get('Date_Admission'), dayfirst=True, errors='coerce')
    ocr_admission = pd.to_datetime(ocr_data.get('Date_Admission'), dayfirst=True, errors='coerce')

    if form_admission != ocr_admission:
        validation_results['updates']['Date_Admission'] = ocr_data.get('Date_Admission')
        validation_results['warnings'].append('Admission date updated to match discharge note')

    # Validate Discharge Date
    form_discharge = pd.to_datetime(form_data.get('Date_Discharge'), dayfirst=True, errors='coerce')
    ocr_discharge = pd.to_datetime(ocr_data.get('Date_Discharge'), dayfirst=True, errors='coerce')

    if form_discharge != ocr_discharge:
        validation_results['updates']['Date_Discharge'] = ocr_data.get('Date_Discharge')
        validation_results['warnings'].append('Discharge date updated to match discharge note')

    # Check for exclusion words in diagnosis
    diagnosis = ocr_data.get('Diagnosis', '').lower()
    found_exclusions = [word for word in EXCLUSION_WORDS if re.search(rf'\b{re.escape(word.lower())}\b', diagnosis)]
    #found_exclusions = [word for word in EXCLUSION_WORDS if word.lower() in diagnosis]
    if found_exclusions:
        validation_results['warnings'].append(f'Second opinion needed: Diagnosis contains terms: {", ".join(found_exclusions)}')

    return validation_results


# In-memory storage for analysis results
results = []

def add_record(record_data, image_embedder, text_index, image_index, records):
    """Add a new record with both text and image embeddings"""
    try:
        print("Generating text embedding...")
        # Generate text embedding
        text_input = f"""
        IC: {record_data['IC']}
        Name: {record_data['Name']}
        Age: {record_data['Age']}
        Doctor: {record_data['Doctor']}
        Specialty: {record_data['Specialty']}
        Hospital: {record_data['Hospital']}
        Date_Admission: {record_data['Date_Admission']}
        Date_Discharge: {record_data['Date_Discharge']}
        Diagnosis: {record_data['Diagnosis']}
        Notes: {record_data['Notes_for_Follow_up']}
        """
        text_embedding = generate_embedding(text_input)

        print("Generating image embedding...")
        # Generate image embedding
        image_embedding = generate_image_embedding(record_data['Image_Path'], image_embedder)

        print("Adding embeddings to indices...")
        # Add embeddings to FAISS indices
        text_index.add(np.array([text_embedding]).astype('float32'))
        image_index.add(np.array([image_embedding]).astype('float32'))

        # Store complete record with embeddings as lists
        record = {
            **record_data,
            'text_embedding': text_embedding.tolist(),
            'image_embedding': image_embedding.tolist(),
            'index_id': len(records)
        }
        records.append(record)

        print(f"Successfully added record with index {record['index_id']}")
        return record['index_id']
    except Exception as e:
        print(f"Error in add_record: {str(e)}")
        raise

pending_claims = {}


def clear_faiss_storage_and_session():
    """Delete FAISS files under APP_ROOT, clear session state, force empty indices.

    Always uses create_empty_indices() after delete — never create_or_load_indices() here,
    or a failed delete would reload old vectors from disk.
    """
    deleted_files = []
    failed_files = []
    for path in (FAISS_TEXT_PATH, FAISS_IMAGE_PATH, FAISS_RECORDS_PATH):
        try:
            if os.path.exists(path):
                os.remove(path)
                deleted_files.append(path)
            else:
                failed_files.append(f"{path} (not found)")
        except Exception as e:
            failed_files.append(f"{path} (error: {str(e)})")
    global results, pending_claims, text_index, image_index, records
    results.clear()
    pending_claims.clear()
    text_index, image_index, records = create_empty_indices()
    save_indices(
        text_index, image_index, records,
        FAISS_TEXT_PATH, FAISS_IMAGE_PATH, FAISS_RECORDS_PATH,
    )
    print(
        f"FAISS cleared: ntext={text_index.ntotal}, nimage={image_index.ntotal}, "
        f"nrecords={len(records)}"
    )
    return deleted_files, failed_files


@app.route('/submit_claim', methods=['POST'])
def submit_claim():
    print(f"\nCurrent database status before processing:")
    print(f"Number of text records: {text_index.ntotal}")
    print(f"Number of image records: {image_index.ntotal}")
    print(f"Number of stored records: {len(records)}")

    request_data = request.json
    form_data = request_data.get('form_data', {})
    ocr_data = request_data.get('ocr_data', {})

    if not form_data or not ocr_data:
        result = {
            'status': 'rejected',
            'error': 'Both form_data and ocr_data are required',
            'form_data': form_data,
            'ocr_data': ocr_data,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        return jsonify(result), 400
    # Update Image_Path to use the uploaded_images folder
    if 'Image_Path' in form_data:
        form_data['Image_Path'] = os.path.join('uploaded_images', form_data['Image_Path'])
    if 'Image_Path' in ocr_data:
        ocr_data['Image_Path'] = os.path.join('uploaded_images', ocr_data['Image_Path'])

    # Generate unique claim ID
    claim_id = str(uuid.uuid4())

    # First validate the claim
    validation_results = validate_claim_data(form_data, ocr_data)

    # Create final claim data by using form data and applying any updates
    final_claim_data = {**form_data, **validation_results['updates']}

    if not validation_results['is_valid']:
        result = {
            'claim_id': claim_id,
            'status': 'rejected',
            'errors': validation_results['errors'],
            'updates': validation_results['updates'],
            'warnings': validation_results['warnings'],
            'form_data': form_data,
            'ocr_data': ocr_data,
            'final_claim_data': final_claim_data,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        # Store the result
        pending_claims[claim_id] = result
        return jsonify(result), 400

    # Proceed with fraud detection if validation passed
    fraud_cases = detect_fraud(final_claim_data, text_index, image_index, records)

    # Prepare the record to be added
    record_to_add = {
        'IC': final_claim_data['IC'],
        'Name': final_claim_data['Patient_Name'],
        'Age': final_claim_data['Age'],
        'Doctor': final_claim_data['Doctor'],
        'Specialty': final_claim_data.get('Specialty', ''),
        'Hospital': final_claim_data['Hospital'],
        'Date_Admission': final_claim_data['Date_Admission'],
        'Date_Discharge': final_claim_data['Date_Discharge'],
        'Diagnosis': final_claim_data['Diagnosis'],
        'Notes_for_Follow_up': final_claim_data['Notes_for_Follow_up'],
        'Image_Path': final_claim_data['Image_Path']
    }

    result = {
        'claim_id': claim_id,
        'status': 'pending_approval' if fraud_cases else 'pending_review',
        'final_claim_data': record_to_add,
        'Analysis_Result': fraud_cases,
        'validation_messages': {
            'warnings': validation_results['warnings'],
            'updates': validation_results['updates']
        },
        'form_data': form_data,
        'ocr_data': ocr_data,
        'timestamp': pd.Timestamp.now().isoformat()
    }

    # Store the pending claim
    pending_claims[claim_id] = {
        'result': result,
        'record_to_add': record_to_add
    }

    return jsonify(result)

@app.route('/approve_claim/<claim_id>', methods=['POST'])
def approve_claim(claim_id):
    """Approve a pending claim and add it to the database"""
    if claim_id not in pending_claims:
        return jsonify({
            'status': 'error',
            'message': 'Claim ID not found'
        }), 404

    pending_claim = pending_claims[claim_id]
    record_to_add = pending_claim['record_to_add']

    try:
        # Add the record to the database
        print("\nAttempting to add approved record to database...")
        add_record(record_to_add, image_embedder, text_index, image_index, records)
        print("Successfully added record")

        # Save updated indices
        save_indices(
            text_index, image_index, records,
            FAISS_TEXT_PATH, FAISS_IMAGE_PATH, FAISS_RECORDS_PATH,
        )
        print("Successfully saved indices")

        # Update the claim status
        pending_claim['result']['status'] = 'approved'

        # Add approval details
        pending_claim['result']['approval_timestamp'] = pd.Timestamp.now().isoformat()
        pending_claim['result']['approved_by'] = request.json.get('approved_by', 'Unknown')

        print(f"\nUpdated database status:")
        print(f"Number of text records: {text_index.ntotal}")
        print(f"Number of image records: {image_index.ntotal}")
        print(f"Number of stored records: {len(records)}")

        return jsonify({
            'status': 'success',
            'message': 'Claim approved and added to database',
            'claim_details': pending_claim['result']
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error adding record: {str(e)}'
        }), 500

@app.route('/reject_claim/<claim_id>', methods=['POST'])
def reject_claim(claim_id):
    """Reject a pending claim"""
    if claim_id not in pending_claims:
        return jsonify({
            'status': 'error',
            'message': 'Claim ID not found'
        }), 404

    pending_claim = pending_claims[claim_id]

    # Update the claim status
    pending_claim['result']['status'] = 'rejected'
    pending_claim['result']['rejection_timestamp'] = pd.Timestamp.now().isoformat()
    pending_claim['result']['rejected_by'] = request.json.get('rejected_by', 'Unknown')
    pending_claim['result']['rejection_reason'] = request.json.get('reason', 'No reason provided')

    return jsonify({
        'status': 'success',
        'message': 'Claim rejected',
        'claim_details': pending_claim['result']
    })

@app.route('/get_claim/<claim_id>', methods=['GET'])
def get_claim(claim_id):
    """Get details of a specific claim"""
    if claim_id not in pending_claims:
        return jsonify({
            'status': 'error',
            'message': 'Claim ID not found'
        }), 404

    return jsonify(pending_claims[claim_id]['result'])

@app.route('/claim/<claim_id>', methods=['DELETE'])
def delete_claim(claim_id):
    """Remove a single claim from the in-memory list."""
    if claim_id not in pending_claims:
        return jsonify({'status': 'error', 'message': 'Claim ID not found'}), 404
    del pending_claims[claim_id]
    return jsonify({'status': 'success', 'message': 'Claim deleted'})


@app.route('/faiss_status', methods=['GET'])
def faiss_status():
    """Debug: current FAISS state (paths are next to app.py)."""
    return jsonify({
        'text_ntotal': text_index.ntotal,
        'image_ntotal': image_index.ntotal,
        'len_records': len(records),
        'text_path': FAISS_TEXT_PATH,
        'image_path': FAISS_IMAGE_PATH,
        'records_path': FAISS_RECORDS_PATH,
    })


@app.route('/claims', methods=['DELETE'])
def delete_all_claims():
    """Clear pending claims and all FAISS embedding storage (full reset)."""
    count = len(pending_claims)
    deleted_files, failed_files = clear_faiss_storage_and_session()
    return jsonify({
        'status': 'success',
        'message': f'Removed {count} claim(s) and cleared FAISS indices',
        'count': count,
        'deleted_files': deleted_files,
        'failed_files': failed_files,
        'faiss_cleared': True,
        'text_ntotal_after_clear': text_index.ntotal,
        'len_records_after_clear': len(records),
    })


@app.route('/get_claims', methods=['GET'])
def get_claims():
    """Get all claims with optional status filter"""
    status = request.args.get('status')

    def get_claim_data(claim):
        """Helper function to handle different claim data structures"""
        if isinstance(claim, dict):
            return claim.get('result', claim)  # Return 'result' if exists, otherwise return claim itself
        return claim

    if status:
        filtered_claims = {
            claim_id: get_claim_data(claim)
            for claim_id, claim in pending_claims.items()
            if get_claim_data(claim).get('status') == status
        }
        return jsonify(filtered_claims)

    return jsonify({
        claim_id: get_claim_data(claim)
        for claim_id, claim in pending_claims.items()
    })

@app.route('/get_results', methods=['GET'])
def get_results():
    # Add filtering capability by status
    status = request.args.get('status')
    if status:
        filtered_results = [r for r in results if r['status'] == status]
        return jsonify(filtered_results)

    # Return all results if no status filter
    return jsonify(results)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    """Handle image upload and return the stored image path"""
    if 'file' not in request.files:
        return jsonify({
            'status': 'error',
            'message': 'No file part'
        }), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'status': 'error',
            'message': 'No selected file'
        }), 400

    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            unique_filename = generate_unique_filename(filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            # Save the file
            file.save(filepath)

            # Return the relative path for future reference
            return jsonify({
                'status': 'success',
                'message': 'File uploaded successfully',
                'image_path': filepath,
                'filename': unique_filename
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error saving file: {str(e)}'
            }), 500
    else:
        return jsonify({
            'status': 'error',
            'message': 'File type not allowed'
        }), 400


@app.route('/get_image/<filename>', methods=['GET'])
def get_image(filename):
    """Retrieve an image by filename"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        return send_file(filepath)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving image: {str(e)}'
        }), 404


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

# Add endpoint to get image upload URL for frontend
@app.route('/get_upload_url', methods=['GET'])
def get_upload_url():
    """Return the URL for image upload"""
    return jsonify({
        'upload_url': request.host_url + 'upload_image'
    })

@app.route('/do_ocr', methods=['GET'])
def do_ocr_url():
    """Extract OCR fields from a hospital discharge note using Gemini, with a fresh session each time."""
    import time as _time

    filepath = request.args.get('file')
    if not filepath:
        return jsonify({"error": "No file specified"}), 400

    filepath = os.path.join(BASE_DIR, "uploaded_images", filepath)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    max_retries = 3
    retry_delays = [45, 60, 90]

    for attempt in range(max_retries):
        try:
            gemini_file = upload_to_gemini(filepath)

            ocr_model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=generation_config,
            )
            chat_session = ocr_model.start_chat(history=[
                {
                    "role": "user",
                    "parts": [
                        (
                            "Extract the following key fields from the OCR output of a hospital discharge note: "
                            "Hospital Name, Name, Age, Sex, Ward, MRN, RN, IC or NRIC (it is a 12 digit value sometimes with - and sometimes without), "
                            "Date of Admission, Date of Discharge, Diagnosis (Include the complete diagnosis), Follow up Notes (May also be named 'Summary'), "
                            "Name of Medical Officer (If no doctor name or medical officer name is found, leave this field empty), and Document Date. "
                            "If a field is not found, return an empty string for that field. "
                            "Return ONLY a valid JSON object, with no markdown, no code block, and no extra text."
                        )
                    ],
                }
            ])
            response_obj = chat_session.send_message(gemini_file)
            print(response_obj)

            json_str = response_obj.candidates[0].content.parts[0].text
            json_str = re.sub(r"^```json|^```|```$", "", json_str).strip()
            response_json = json.loads(json_str)
            return response_json

        except Exception as e:
            error_str = str(e)
            is_quota_error = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()

            if is_quota_error and attempt < max_retries - 1:
                wait = retry_delays[attempt]
                print(f"[OCR] Gemini quota exceeded (attempt {attempt + 1}/{max_retries}), retrying in {wait}s...")
                _time.sleep(wait)
                continue

            print(f"[OCR] Failed after {attempt + 1} attempt(s): {error_str}")
            if is_quota_error:
                return jsonify({
                    "error": "Gemini API rate limit exceeded. The free tier has very low limits. Please wait 1-2 minutes and try again, or upgrade to a paid Gemini API plan."
                }), 429
            return jsonify({"error": f"OCR extraction failed: {error_str}"}), 500

@app.route('/reset_app', methods=['GET'])
def reset_app():
    """Reset the app by deleting index and records files and clearing in-memory data."""
    deleted_files, failed_files = clear_faiss_storage_and_session()
    return jsonify({
        'status': 'success',
        'deleted_files': deleted_files,
        'failed_files': failed_files,
        'results_cleared': True,
        'pending_claims_cleared': True,
        'indices_reloaded': True
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8004))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

