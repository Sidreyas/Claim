
import faiss
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python import text
import pickle
import os
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv('AZURE_OPENAI_API_KEY_VISION')
openai.api_base = os.getenv('AZURE_OPENAI_ENDPOINT_VISION')
openai.api_type = 'azure'
openai.api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2023-03-15-preview')

def generate_embedding(text):
    response = openai.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    embedding = response.data[0].embedding
    return np.array(embedding)

def init_embedders(image_model_path='embedder.tflite', text_model_path='text_embedder.tflite'):
    """Initialize MediaPipe embedders for both image and text"""
    # Image embedder initialization
    image_base_options = python.BaseOptions(model_asset_path=image_model_path)
    image_options = vision.ImageEmbedderOptions(
        base_options=image_base_options,
        l2_normalize=True,
        quantize=True
    )
    image_embedder = vision.ImageEmbedder.create_from_options(image_options)

    # Text embedder initialization
    text_base_options = python.BaseOptions(model_asset_path=text_model_path)
    text_options = text.TextEmbedderOptions(
        base_options=text_base_options,
        l2_normalize=True
    )
    text_embedder = text.TextEmbedder.create_from_options(text_options)

    return image_embedder, text_embedder


def generate_image_embedding(image_path, image_embedder):
    """Generate embedding for image using MediaPipe"""
    image = mp.Image.create_from_file(image_path)
    embedding_result = image_embedder.embed(image)
    embedding = embedding_result.embeddings[0].embedding
    # Normalize the embedding
    embedding = np.array(embedding)
    embedding = embedding / np.linalg.norm(embedding)
    return embedding



def save_indices(text_index, image_index, records, text_index_path='text_index.faiss',
                image_index_path='image_index.faiss', records_path='records.pkl'):
    """Save FAISS indices and records to disk"""
    faiss.write_index(text_index, text_index_path)
    faiss.write_index(image_index, image_index_path)
    with open(records_path, 'wb') as f:
        pickle.dump(records, f)
    print("Indices and records saved to disk")

def create_or_load_indices(text_index_path='text_index.faiss',
                          image_index_path='image_index.faiss',
                          records_path='records.pkl'):
    """Create new or load existing FAISS indices"""
    # OpenAI text embedding dimension
    text_dimension = 1536  # Ada-002 embedding dimension
    # MediaPipe image embedder dimension
    image_dimension = 1024

    if os.path.exists(text_index_path) and os.path.exists(image_index_path) and os.path.exists(records_path):
        print("Loading existing indices")
        text_index = faiss.read_index(text_index_path)
        image_index = faiss.read_index(image_index_path)
        with open(records_path, 'rb') as f:
            records = pickle.load(f)
    else:
        print("Creating new indices")
        text_index = faiss.IndexFlatL2(text_dimension)
        image_index = faiss.IndexFlatL2(image_dimension)
        records = []

    return text_index, image_index, records


def create_empty_indices():
    """Fresh empty FAISS indices and records list (same dimensions as create_or_load_indices)."""
    text_dimension = 1536
    image_dimension = 1024
    text_index = faiss.IndexFlatL2(text_dimension)
    image_index = faiss.IndexFlatL2(image_dimension)
    return text_index, image_index, []


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

def detect_fraud(new_claim, image_embedder, text_index, image_index, records,
                k=5, text_threshold=0.90, image_threshold=0.85):
    """Detect potential fraud using both text and image similarity"""
    print(f"\nChecking against {text_index.ntotal} existing records")

    # Generate text embedding using OpenAI
    text_input = f"""
    Doctor: {new_claim['Doctor']}
    Diagnosis: {new_claim['Diagnosis']}
    Hospital: {new_claim['Hospital']}
    Notes: {new_claim['Notes_for_Follow_up']}
    """
    new_text_embedding = generate_embedding(text_input).astype('float32').reshape(1, -1)

    # Generate image embedding using MediaPipe
    new_image_embedding = generate_image_embedding(new_claim['Image_Path'], image_embedder).astype('float32').reshape(1, -1)

    print(f"\nNew claim details:")
    print(f"IC: {new_claim['IC']}")
    print(f"Image: {new_claim['Image_Path']}")

    # Search similar text embeddings
    text_distances, text_indices = text_index.search(new_text_embedding, k)

    suspicious_claims = []

    # Analyze filtered results
    for i, idx in enumerate(text_indices[0]):
        if idx == -1:  # FAISS returns -1 for empty slots
            continue

        record = records[idx]

        # Calculate similarities
        text_similarity = 1 - (text_distances[0][i] / 2)

        print(f"\nAnalyzing record {idx}:")
        print(f"IC: {record['IC']}")
        print(f"Image: {record['Image_Path']}")
        print(f"Text similarity: {text_similarity*100:.2f}%")

        fraud_details = {
            'matched_record': record,
            'text_similarity': float(text_similarity),
            'fraud_indicators': []
        }

        # Check text similarity first
        if text_similarity >= text_threshold:
            print("⚠️ High text similarity detected!")
            fraud_details['fraud_indicators'].append(f"High text similarity ({text_similarity*100:.2f}%)")

            # Only check image if text is suspicious
            image_distances, _ = image_index.search(new_image_embedding, 1)
            image_similarity = 1 - (image_distances[0][0] / 2)
            fraud_details['image_similarity'] = float(image_similarity)

            print(f"Image similarity: {image_similarity*100:.2f}%")
            print(f"Comparing images:")
            print(f"  New image: {new_claim['Image_Path']}")
            print(f"  Matched image: {record['Image_Path']}")

            if image_similarity >= image_threshold:
                print("⚠️ Similar images detected!")
                fraud_details['fraud_indicators'].append(f"Similar images ({image_similarity*100:.2f}%)")

            if fraud_details['fraud_indicators']:
                suspicious_claims.append(fraud_details)

    return suspicious_claims

def process_new_claim(claim_data, image_path):
    """Process a new claim and check for potential fraud"""
    try:
        # Initialize only image embedder (OpenAI doesn't need initialization)
        image_embedder, _ = init_embedders()

        # Load or create indices
        text_index, image_index, records = create_or_load_indices()

        # Prepare new claim
        new_claim = {
            **claim_data,
            'Image_Path': image_path
        }

        # Check for fraud
        suspicious_matches = detect_fraud(new_claim, image_embedder, text_index, image_index, records)

        if suspicious_matches:
            print("\nPotential fraud detected!")
            for match in suspicious_matches:
                print(f"\nMatched Record Details:")
                print(f"IC: {match['matched_record']['IC']}")
                print(f"Name: {match['matched_record']['Name']}")
                print(f"Hospital: {match['matched_record']['Hospital']}")
                print(f"Doctor: {match['matched_record']['Doctor']}")
                print(f"Image Path: {match['matched_record']['Image_Path']}")
                print(f"Text Similarity: {match['text_similarity']*100:.2f}%")
                print(f"Image Similarity: {match['image_similarity']*100:.2f}%")
                print("Fraud Indicators:", ", ".join(match['fraud_indicators']))
        else:
            print("\nNo suspicious matches found")
            # Add the new claim to the indices
            add_record(new_claim, image_embedder, text_index, image_index, records)
            print("New claim added to database")

        # Save indices and records after processing
        save_indices(text_index, image_index, records)

    finally:
        if 'image_embedder' in locals():
            image_embedder.close()

# Example claim data
claim_data = {
    'IC': "960707146352",
    'Name': "JASPREET KAUR",
    'Age': 28,
    'Doctor': "Aiman Ishak",
    'Specialty': "Cardiology",
    'Hospital': "SABAH WOMENAND CHILDREN HOSPITAL",
    'Date_Admission': "2024-12-12",
    'Date_Discharge': "2024-12-16",
    'Diagnosis': "Brain biopsy confirmed glioblastoma multiforme.",
    'Notes_for_Follow_up': "This patient received a six week course or radiation and will start a phase 2 clinical chemotherapy trial at the NIH. He was also started on seizure prophylaxis and pain medication."
}

claim_data2 = {
    'IC': "000404011234",
    'Name': "SYA",
    'Age': 27,
    'Doctor': "Reid",
    'Specialty': "Cardiology",
    'Hospital': "SABAH WOMENAND CHILDREN HOSPITAL",
    'Date_Admission': "2024-12-10",
    'Date_Discharge': "2024-12-24",
    'Diagnosis': "Pulmonary artery pseudoaneurysm secondary to erosion of tumor into the wall of the middle lobar branches of the right pulomary artery and obstruction of superior lobar branches of the right pulmonary artery due to mass effect from the tumor.",
    'Notes_for_Follow_up': "Conventional pulmonary arteriography and coiling."
}

claim_data3 = {
    'IC': "000404011234",
    'Name': "hello",
    'Age': 27,
    'Doctor': "Reid",
    'Specialty': "Cardiology",
    'Hospital': "SABAH WOMENAND CHILDREN HOSPITAL",
    'Date_Admission': "2024-12-10",
    'Date_Discharge': "2024-12-24",
    'Diagnosis': " artery pseudoaneurysm secondary to of the middle lobar branches of the right pulomary artery and obstruction of superior  of the right pulmonary artery due to mass effect from the tumor.",
    'Notes_for_Follow_up': "Conventional pulmonary  and coiling."
}
# Process new claim
#process_new_claim(claim_data, "same_hospital_1.jpg")
#process_new_claim(claim_data2, "same_hospital_2.jpg")
#process_new_claim(claim_data3, "New record to compare.jpg")