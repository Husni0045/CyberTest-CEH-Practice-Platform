import os
import random

from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise RuntimeError('MONGO_URI environment variable is not set. Define it before running questions_manager.')

DB_NAME = os.environ.get('MONGO_DB_NAME', 'cybertest_db')
QUESTIONS_COLLECTION = os.environ.get('MONGO_QUESTIONS_COLLECTION', 'questions')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[QUESTIONS_COLLECTION]

def create_question(question, options, correct, version):
    return {
        "_id": str(ObjectId()),
        "question": question,
        "options": options,
        "correct": correct,
        "version": version
    }

# Base questions per version
questions = {
    "12": [
        ("Which protocol is used to securely browse websites?", 
         ["HTTP", "FTP", "SSH", "HTTPS"], "HTTPS"),
        ("What is the primary purpose of a firewall?",
         ["Network security", "Data encryption", "Password management", "File sharing"], 
         "Network security"),
        ("What is a common tool for penetration testing?",
         ["Metasploit", "Microsoft Word", "Chrome", "Notepad"],
         "Metasploit"),
    ],
    "11": [
        ("Which tool is commonly used for packet sniffing?",
         ["Wireshark", "Metasploit", "Nmap", "Aircrack-ng"],
         "Wireshark"),
        ("What type of attack is SQL injection?",
         ["Application layer", "Network layer", "Physical layer", "Data link layer"],
         "Application layer"),
        ("Which protocol is connectionless?",
         ["UDP", "TCP", "HTTP", "FTP"],
         "UDP"),
    ],
    "10": [
        ("What does SQL stand for?",
         ["Structured Query Language", "Strong Question Language", "System Query Logic", "Simple Query Line"],
         "Structured Query Language"),
        ("Which encryption algorithm is asymmetric?",
         ["AES", "RSA", "DES", "3DES"],
         "RSA"),
        ("What is the purpose of a VPN?",
         ["Secure remote access", "File sharing", "Web hosting", "Email service"],
         "Secure remote access"),
    ]
}

def seed_database():
    # Clear existing questions
    collection.delete_many({})
    
    all_questions = []
    
    # Process each version
    for version, base_qs in questions.items():
        version_questions = []
        
        # Create base questions for this version
        for q, opts, ans in base_qs:
            version_questions.append(create_question(q, opts, ans, version))
        
        # Generate additional questions to reach 125
        while len(version_questions) < 125:
            template = random.choice(version_questions)
            new_q = template.copy()
            new_q["_id"] = str(ObjectId())
            new_q["question"] = f"CEHv{version}: {new_q['question']}"
            version_questions.append(new_q)
        
        all_questions.extend(version_questions)
    
    # Insert all questions
    collection.insert_many(all_questions)
    print(f"✅ Added {len(all_questions)} questions successfully!")
    print(f"Questions per version: {len(all_questions) // len(questions)}")

if __name__ == "__main__":
    seed_database()