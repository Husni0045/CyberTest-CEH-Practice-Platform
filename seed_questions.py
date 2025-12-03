import os

from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise RuntimeError('MONGO_URI environment variable is not set. Define it before running the seed script.')

DB_NAME = os.environ.get('MONGO_DB_NAME', 'cybertest_db')
QUESTIONS_COLLECTION = os.environ.get('MONGO_QUESTIONS_COLLECTION', 'questions')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[QUESTIONS_COLLECTION]

ACTIVE_VERSION = "12"

questions = [
    # Network Security (1-25)
    {
        "_id": str(ObjectId()),
    "version": ACTIVE_VERSION,
        "question": "Which protocol is used to securely browse websites?",
        "options": ["HTTP", "FTP", "SSH", "HTTPS"],
        "correct": "HTTPS"
    },
    # ... Add more network security questions here
    
    # System Security (26-50)
    {
        "_id": str(ObjectId()),
    "version": ACTIVE_VERSION,
        "question": "Which tool is used for packet sniffing?",
        "options": ["Wireshark", "Metasploit", "Nmap", "Aircrack-ng"],
        "correct": "Wireshark"
    },
    # ... Add more system security questions here
    
    # Web Security (51-75)
    {
        "_id": str(ObjectId()),
    "version": ACTIVE_VERSION,
        "question": "What does SQL stand for?",
        "options": ["Structured Query Language", "Strong Question Language", "System Query Logic", "Simple Query Line"],
        "correct": "Structured Query Language"
    },
    # ... Add more web security questions here
    
    # Cryptography (76-100)
    {
        "_id": str(ObjectId()),
    "version": ACTIVE_VERSION,
        "question": "Which encryption algorithm is considered asymmetric?",
        "options": ["AES", "RSA", "DES", "3DES"],
        "correct": "RSA"
    },
    # ... Add more cryptography questions here
    
    # General Security Concepts (101-125)
    {
        "_id": str(ObjectId()),
    "version": ACTIVE_VERSION,
        "question": "What is the primary goal of CIA triad in information security?",
        "options": [
            "Confidentiality, Integrity, Availability",
            "Control, Infrastructure, Access",
            "Cybersecurity, Infrastructure, Authentication",
            "Cryptography, Identity, Authorization"
        ],
        "correct": "Confidentiality, Integrity, Availability"
    }
    # ... Add more general security questions here
]

# Generate remaining questions programmatically to reach 125
base_questions = questions.copy()
# Expand base questions to reach 125, keeping everything on the active version
while len(questions) < 125:
    for q in base_questions:
        if len(questions) >= 125:
            break
        new_q = q.copy()
        new_q["_id"] = str(ObjectId())
        new_q["version"] = ACTIVE_VERSION
        questions.append(new_q)

collection.insert_many(questions)
print("✅ Questions added successfully!")
