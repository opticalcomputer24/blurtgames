from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from jose import JWTError, jwt
from beem import Blurt
from beem.account import Account
from beem.exceptions import AccountDoesNotExistsException
import asyncio
import traceback

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# JWT settings
SECRET_KEY = "blurt_quest_secret_key_2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Blurt settings
blurt_instance = Blurt()

# Define Models
class BlurtAuthRequest(BaseModel):
    username: str
    posting_key: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    username: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    current_level: int = 1
    completed_levels: List[int] = []
    total_score: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

class QuizQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    level: int
    question: str
    options: List[str]
    correct_answer: int  # Index of correct option
    points: int
    category: str  # "general", "technology", "crypto", "blurt"

class LevelCompletion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    level: int
    score: int
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    questions_answered: int
    time_taken_seconds: int

class RewardClaim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    level: int
    reward_amount: float  # Blurt tokens
    claimed_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, processed

# Helper Functions
async def verify_blurt_posting_key(username: str, posting_key: str) -> bool:
    """Verify Blurt posting key for the given username"""
    try:
        loop = asyncio.get_event_loop()
        
        def check_key():
            try:
                account = Account(username, blockchain_instance=blurt_instance)
                # Check if the posting key is valid for this account
                return account.posting_keys[0] == posting_key or posting_key in account.posting_keys
            except AccountDoesNotExistsException:
                return False
            except Exception as e:
                logging.error(f"Error verifying key: {str(e)}")
                return False
        
        result = await loop.run_in_executor(None, check_key)
        return result
    except Exception as e:
        logging.error(f"Error in verify_blurt_posting_key: {str(e)}")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username

# Initialize quiz questions
async def init_quiz_questions():
    """Initialize quiz questions if not exists"""
    existing_count = await db.quiz_questions.count_documents({})
    if existing_count == 0:
        questions = [
            # Level 1 - General Knowledge
            {"level": 1, "question": "What is the largest planet in our solar system?", "options": ["Earth", "Jupiter", "Saturn", "Mars"], "correct_answer": 1, "points": 10, "category": "general"},
            {"level": 1, "question": "Which element has the chemical symbol 'O'?", "options": ["Gold", "Silver", "Oxygen", "Iron"], "correct_answer": 2, "points": 10, "category": "general"},
            {"level": 1, "question": "What is the capital of France?", "options": ["London", "Berlin", "Madrid", "Paris"], "correct_answer": 3, "points": 10, "category": "general"},
            
            # Level 2 - Technology
            {"level": 2, "question": "What does 'HTTP' stand for?", "options": ["HyperText Transfer Protocol", "High Tech Transfer Protocol", "Home Tool Transfer Protocol", "Hyper Transfer Text Protocol"], "correct_answer": 0, "points": 15, "category": "technology"},
            {"level": 2, "question": "Which programming language is known as the 'language of the web'?", "options": ["Python", "Java", "JavaScript", "C++"], "correct_answer": 2, "points": 15, "category": "technology"},
            {"level": 2, "question": "What does 'AI' commonly stand for?", "options": ["Automated Intelligence", "Artificial Intelligence", "Advanced Integration", "Application Interface"], "correct_answer": 1, "points": 15, "category": "technology"},
            
            # Level 3 - Crypto & Blockchain
            {"level": 3, "question": "What is the first cryptocurrency?", "options": ["Ethereum", "Litecoin", "Bitcoin", "Ripple"], "correct_answer": 2, "points": 20, "category": "crypto"},
            {"level": 3, "question": "What does 'DeFi' stand for?", "options": ["Decentralized Finance", "Digital Finance", "Distributed Finance", "Direct Finance"], "correct_answer": 0, "points": 20, "category": "crypto"},
            {"level": 3, "question": "What is a blockchain?", "options": ["A type of database", "A distributed ledger", "A chain of blocks containing data", "All of the above"], "correct_answer": 3, "points": 20, "category": "crypto"},
            
            # Level 4 - Blurt Basics
            {"level": 4, "question": "Blurt is a fork of which blockchain?", "options": ["Bitcoin", "Ethereum", "Steem", "Hive"], "correct_answer": 2, "points": 25, "category": "blurt"},
            {"level": 4, "question": "What is the native token of the Blurt blockchain?", "options": ["BLURT", "STEEM", "HIVE", "BTC"], "correct_answer": 0, "points": 25, "category": "blurt"},
            {"level": 4, "question": "Blurt focuses on which primary activity?", "options": ["Gaming", "Social blogging", "DeFi", "NFTs"], "correct_answer": 1, "points": 25, "category": "blurt"},
            
            # Level 5 - Mixed Advanced
            {"level": 5, "question": "What is the process of validating transactions on a blockchain called?", "options": ["Mining", "Staking", "Consensus", "All of the above"], "correct_answer": 3, "points": 30, "category": "crypto"},
            {"level": 5, "question": "Which of these is NOT a programming paradigm?", "options": ["Object-Oriented", "Functional", "Procedural", "Blockchain"], "correct_answer": 3, "points": 30, "category": "technology"},
            {"level": 5, "question": "What does 'WWW' stand for?", "options": ["World Wide Web", "World Wide Wait", "World Wide Width", "World Wide Work"], "correct_answer": 0, "points": 30, "category": "technology"},
            
            # Level 6 - Environment & Tech
            {"level": 6, "question": "What is the main greenhouse gas responsible for climate change?", "options": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Helium"], "correct_answer": 2, "points": 35, "category": "general"},
            {"level": 6, "question": "Which renewable energy source uses the sun?", "options": ["Wind", "Solar", "Hydro", "Geothermal"], "correct_answer": 1, "points": 35, "category": "general"},
            {"level": 6, "question": "What does 'IoT' stand for?", "options": ["Internet of Things", "Integration of Technology", "Interface of Tools", "Internet of Technology"], "correct_answer": 0, "points": 35, "category": "technology"},
            
            # Level 7 - Advanced Crypto
            {"level": 7, "question": "What is a smart contract?", "options": ["A legal document", "Self-executing code on blockchain", "A trading algorithm", "A mining contract"], "correct_answer": 1, "points": 40, "category": "crypto"},
            {"level": 7, "question": "What is 'HODL' in crypto?", "options": ["Hold On for Dear Life", "A typo for 'hold'", "A trading strategy", "All of the above"], "correct_answer": 3, "points": 40, "category": "crypto"},
            {"level": 7, "question": "What is a private key in cryptocurrency?", "options": ["Public address", "Secret key for wallet access", "Transaction ID", "Block hash"], "correct_answer": 1, "points": 40, "category": "crypto"},
            
            # Level 8 - Blurt Advanced
            {"level": 8, "question": "What is the block time for Blurt blockchain?", "options": ["1 minute", "3 seconds", "10 minutes", "30 seconds"], "correct_answer": 1, "points": 45, "category": "blurt"},
            {"level": 8, "question": "Blurt allows content creators to earn through?", "options": ["Proof of Work", "Proof of Stake", "Proof of Brain", "Proof of Authority"], "correct_answer": 2, "points": 45, "category": "blurt"},
            {"level": 8, "question": "What makes Blurt different from Steem?", "options": ["No downvoting", "Faster blocks", "Different rewards", "All of the above"], "correct_answer": 3, "points": 45, "category": "blurt"},
            
            # Level 9 - Expert Level
            {"level": 9, "question": "What is the Byzantine Generals Problem?", "options": ["A historical battle", "A consensus problem in distributed systems", "A cryptographic puzzle", "A game theory concept"], "correct_answer": 1, "points": 50, "category": "crypto"},
            {"level": 9, "question": "Which consensus mechanism does Blurt use?", "options": ["Proof of Work", "Proof of Stake", "Delegated Proof of Stake", "Proof of Authority"], "correct_answer": 2, "points": 50, "category": "blurt"},
            {"level": 9, "question": "What is sharding in blockchain?", "options": ["Breaking chains", "Splitting network into smaller pieces", "Creating forks", "Mining technique"], "correct_answer": 1, "points": 50, "category": "crypto"},
            
            # Level 10 - Master Level
            {"level": 10, "question": "What is the trilemma in blockchain?", "options": ["Speed, Cost, Security", "Scalability, Security, Decentralization", "Privacy, Speed, Cost", "Consensus, Mining, Staking"], "correct_answer": 1, "points": 100, "category": "crypto"},
            {"level": 10, "question": "Who can become a witness on Blurt?", "options": ["Only developers", "Anyone with enough votes", "Only founders", "Only miners"], "correct_answer": 1, "points": 100, "category": "blurt"},
            {"level": 10, "question": "What is the ultimate goal of blockchain technology?", "options": ["Make money", "Decentralization and trustlessness", "Replace banks", "Create cryptocurrencies"], "correct_answer": 1, "points": 100, "category": "crypto"},
        ]
        
        for q in questions:
            question_obj = QuizQuestion(**q)
            await db.quiz_questions.insert_one(question_obj.dict())
        
        logging.info(f"Initialized {len(questions)} quiz questions")

# Authentication Routes
@api_router.post("/auth/login", response_model=AuthResponse)
async def login(auth_request: BlurtAuthRequest):
    """Authenticate user with Blurt posting key"""
    try:
        # Verify the posting key
        is_valid = await verify_blurt_posting_key(auth_request.username, auth_request.posting_key)
        
        if not is_valid:
            raise HTTPException(
                status_code=401,
                detail="Invalid Blurt username or posting key"
            )
        
        # Check if user exists, if not create new user
        existing_user = await db.users.find_one({"username": auth_request.username})
        if not existing_user:
            new_user = User(username=auth_request.username)
            await db.users.insert_one(new_user.dict())
        else:
            # Update last active
            await db.users.update_one(
                {"username": auth_request.username},
                {"$set": {"last_active": datetime.utcnow()}}
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": auth_request.username}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": auth_request.username
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Authentication failed")

# Game Routes
@api_router.get("/user/profile")
async def get_user_profile(current_user: str = Depends(get_current_user)):
    """Get current user's profile and progress"""
    user = await db.users.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": user["username"],
        "current_level": user["current_level"],
        "completed_levels": user["completed_levels"],
        "total_score": user["total_score"],
        "levels_completed": len(user["completed_levels"]),
        "next_level": user["current_level"] if user["current_level"] <= 10 else None
    }

@api_router.get("/game/level/{level}")
async def get_level_questions(level: int, current_user: str = Depends(get_current_user)):
    """Get questions for a specific level"""
    if level < 1 or level > 10:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    # Check if user can access this level
    user = await db.users.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if level > user["current_level"]:
        raise HTTPException(status_code=403, detail="Level not unlocked yet")
    
    # Get questions for this level
    questions = await db.quiz_questions.find({"level": level}).to_list(100)
    
    # Remove correct answers from response
    for q in questions:
        q.pop("correct_answer", None)
    
    return {
        "level": level,
        "questions": questions,
        "total_questions": len(questions)
    }

@api_router.post("/game/level/{level}/submit")
async def submit_level(
    level: int, 
    answers: List[int], 
    time_taken: int,
    current_user: str = Depends(get_current_user)
):
    """Submit answers for a level"""
    if level < 1 or level > 10:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    # Get user and verify access
    user = await db.users.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if level > user["current_level"]:
        raise HTTPException(status_code=403, detail="Level not unlocked yet")
    
    # Get correct answers
    questions = await db.quiz_questions.find({"level": level}).to_list(100)
    if len(answers) != len(questions):
        raise HTTPException(status_code=400, detail="Invalid number of answers")
    
    # Calculate score
    correct_answers = 0
    total_points = 0
    
    for i, question in enumerate(questions):
        if i < len(answers) and answers[i] == question["correct_answer"]:
            correct_answers += 1
            total_points += question["points"]
    
    # Level completion threshold (need at least 60% correct)
    passing_score = len(questions) * 0.6
    level_completed = correct_answers >= passing_score
    
    # Save level completion
    completion = LevelCompletion(
        username=current_user,
        level=level,
        score=total_points,
        questions_answered=len(answers),
        time_taken_seconds=time_taken
    )
    await db.level_completions.insert_one(completion.dict())
    
    # Update user progress if level completed and not already completed
    if level_completed and level not in user["completed_levels"]:
        updated_completed = user["completed_levels"] + [level]
        new_current_level = min(level + 1, 10) if level == user["current_level"] else user["current_level"]
        new_total_score = user["total_score"] + total_points
        
        await db.users.update_one(
            {"username": current_user},
            {"$set": {
                "completed_levels": updated_completed,
                "current_level": new_current_level,
                "total_score": new_total_score,
                "last_active": datetime.utcnow()
            }}
        )
        
        # Create reward claim
        reward_amount = level * 1.0  # 1 BLURT per level, increasing
        reward = RewardClaim(
            username=current_user,
            level=level,
            reward_amount=reward_amount
        )
        await db.reward_claims.insert_one(reward.dict())
    
    return {
        "level": level,
        "correct_answers": correct_answers,
        "total_questions": len(questions),
        "score": total_points,
        "level_completed": level_completed,
        "passing_score_needed": passing_score,
        "next_level_unlocked": level_completed and level < 10,
        "reward_earned": level * 1.0 if level_completed and level not in user["completed_levels"] else 0
    }

@api_router.get("/game/leaderboard")
async def get_leaderboard():
    """Get top players leaderboard"""
    users = await db.users.find().sort("total_score", -1).limit(20).to_list(20)
    
    leaderboard = []
    for i, user in enumerate(users):
        leaderboard.append({
            "rank": i + 1,
            "username": user["username"],
            "total_score": user["total_score"],
            "levels_completed": len(user["completed_levels"]),
            "current_level": user["current_level"]
        })
    
    return {"leaderboard": leaderboard}

# Admin Routes
@api_router.get("/admin/users")
async def get_all_users():
    """Get all users for admin (simplified endpoint)"""
    users = await db.users.find().sort("total_score", -1).to_list(1000)
    return {"users": users}

@api_router.get("/admin/rewards")
async def get_reward_claims():
    """Get all reward claims for admin"""
    rewards = await db.reward_claims.find().sort("claimed_at", -1).to_list(1000)
    return {"rewards": rewards}

@api_router.get("/admin/export/rewards")
async def export_rewards():
    """Export rewards in CSV format for manual distribution"""
    rewards = await db.reward_claims.find({"status": "pending"}).to_list(1000)
    
    csv_data = []
    total_rewards = 0
    
    for reward in rewards:
        csv_data.append({
            "username": reward["username"],
            "level": reward["level"],
            "reward_amount": reward["reward_amount"],
            "claimed_at": reward["claimed_at"].isoformat(),
            "status": reward["status"]
        })
        total_rewards += reward["reward_amount"]
    
    return {
        "rewards": csv_data,
        "total_pending_rewards": total_rewards,
        "total_claims": len(csv_data)
    }

# Basic routes
@api_router.get("/")
async def root():
    return {"message": "Blurt Quest: Puzzle for Tokens API"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize data on startup"""
    await init_quiz_questions()
    logger.info("Blurt Quest API started successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
