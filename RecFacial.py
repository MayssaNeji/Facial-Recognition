from flask import Flask, request, jsonify
import face_recognition
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import io
import os

app = Flask(__name__)


cred_path = r"C:\Users\mayssa\Desktop\MR Resrvation\recFacial\reservation-mr-86484-firebase-adminsdk-fbsvc-5de759e92e.json"


if not os.path.exists(cred_path):
    print(f"Error: Service account key file not found at {cred_path}")
    exit(1)

try:

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

   
    test_doc_ref = db.collection('test_collection').document('test_document')
    test_doc_ref.set({
        'status': 'connected',
        'timestamp': firestore.SERVER_TIMESTAMP
    })
    print("Successfully wrote to Firestore!")

    
    doc = test_doc_ref.get()
    if doc.exists:
        print(f"Document data: {doc.to_dict()}")
    else:
        print("Document was not found!")

except Exception as e:
    print(f"Error: {str(e)}")

@app.route('/upload-known-face', methods=['POST'])
def upload_known_face():
    if 'image' not in request.files or 'name' not in request.form:
        return jsonify({"error": "Image and name are required"}), 400

    image_file = request.files['image']
    name = request.form['name']


    try:
        image = face_recognition.load_image_file(image_file)
        encodings = face_recognition.face_encodings(image)

        if not encodings:
            return jsonify({"error": "No faces found in the image"}), 400

        # Store the first face encoding in Firebase
        encoding = encodings[0].tolist()  # Convert numpy array to list for Firestore
        db.collection('known_faces').document(name).set({
            'name': name,
            'encoding': encoding
        })

        return jsonify({"message": f"Face encoding for {name} stored successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/recognize-face', methods=['POST'])
def recognize_face():
    if 'image' not in request.files:
        return jsonify({"error": "Image is required"}), 400

    image_file = request.files['image']

    try:
        image = face_recognition.load_image_file(image_file)
        unknown_encodings = face_recognition.face_encodings(image)

        if not unknown_encodings:
            return jsonify({"error": "No faces found in the image"}), 400

        unknown_encoding = unknown_encodings[0] 

    
        known_faces = db.collection('known_faces').stream()
        known_encodings = []
        known_names = []

        for face in known_faces:
            data = face.to_dict()
            known_encodings.append(np.array(data['encoding']))
            known_names.append(data['name'])

 
        matches = face_recognition.compare_faces(known_encodings, unknown_encoding, tolerance=0.6)
        if True in matches:
            match_index = matches.index(True)
            return jsonify({"recognized": known_names[match_index]}), 200
        else:
            return jsonify({"message": "No match found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)