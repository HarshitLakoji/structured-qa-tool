from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from .database import engine, get_db
from . import models
from .auth import hash_password, verify_password, create_access_token, get_current_user
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials
from .auth import security
from fastapi import UploadFile, File
import shutil
import os
from .rag import add_document_to_vectorstore
from pydantic import BaseModel
from .rag import generate_answer, generate_answers_batch
import re
from pypdf import PdfReader
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi import Form
from jose import jwt
from .auth import SECRET_KEY, ALGORITHM
from fastapi.responses import FileResponse
from fastapi.responses import FileResponse
from fastapi.responses import FileResponse
import re
import os



class QuestionRequest(BaseModel):
    question: str

class UpdateAnswerRequest(BaseModel):
    answer_text: str

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

class UserCreate(BaseModel):
    email: str
    password: str


@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(user.password)
    new_user = models.User(email=user.email, password_hash=hashed)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}


@app.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"sub": db_user.email})

    return {"access_token": token}


@app.get("/me")
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return {"email": current_user.email}

@app.post("/upload-reference")
def upload_reference(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_location = f"{upload_dir}/{file.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if file.filename.endswith(".txt"):
        with open(file_location, "r", encoding="utf-8") as f:
            content = f.read()

    elif file.filename.endswith(".pdf"):
        reader = PdfReader(file_location)
        content = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                content += text + "\n"

    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    new_doc = models.Document(
        filename=file.filename,
        file_path=file_location,
        owner_id=current_user.id
    )

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # Add to vector DB
    add_document_to_vectorstore(
        new_doc.id,
        content,
        current_user.id,
        new_doc.filename
    )

    return {"message": "File uploaded and indexed successfully"}

@app.post("/ask")
def ask_question(
    request: QuestionRequest,
    current_user: models.User = Depends(get_current_user)
):
    result = generate_answer(request.question,current_user.id)
    return result


@app.post("/upload-questionnaire")
def upload_questionnaire(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_location = f"{upload_dir}/{file.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract text
    if file.filename.endswith(".txt"):
        with open(file_location, "r", encoding="utf-8") as f:
            content = f.read()

    elif file.filename.endswith(".pdf"):
        reader = PdfReader(file_location)
        content = ""
        for page in reader.pages:
            content += page.extract_text() + "\n"

    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    # Store questionnaire
    new_questionnaire = models.Questionnaire(
        filename=file.filename,
        file_path=file_location,
        owner_id=current_user.id
    )

    db.add(new_questionnaire)
    db.commit()
    db.refresh(new_questionnaire)

    
    clean_text = re.sub(r'\s+', ' ', content).strip()

    # Split based on numbering like "1. ", "2. ", "10. "
    raw_questions = re.split(r'\s(?=\d+\.\s)', clean_text)

    questions = []

    for q in raw_questions:
        q = q.strip()
        if not q:
            continue

        # Remove numbering like "1. "
        clean_question = re.sub(r'^\d+\.\s*', '', q)

        # Only keep meaningful entries
        if len(clean_question) > 10:
            questions.append(clean_question)

    for idx, q in enumerate(questions):
        new_question = models.Question(
            questionnaire_id=new_questionnaire.id,
            question_text=q,
            order_index=idx
        )
        db.add(new_question)

    db.commit()

    return {
        "message": "Questionnaire uploaded successfully",
        "questionnaire_id": new_questionnaire.id,
        "total_questions": len(questions)
    }

@app.post("/generate-answers/{questionnaire_id}")
def generate_answers(
    questionnaire_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    questions = db.query(models.Question).filter(
        models.Question.questionnaire_id == questionnaire_id
    ).order_by(models.Question.order_index).all()

    if not questions:
        raise HTTPException(status_code=404, detail="No questions found")

    question_texts = [q.question_text for q in questions]

    batch_results = generate_answers_batch(question_texts, current_user.id)

    answers_to_save = []
    results = []

    for question in questions:

        matched = next(
            (r for r in batch_results if r["question"] == question.question_text),
            None
        )

        if not matched:
            continue
        confidence = matched.get("confidence", "Medium")
        
        new_answer = models.Answer(
            question_id=question.id,
            answer_text=matched["answer"],
            citations="\n".join(matched["citations"]),
            confidence=confidence
        )

        answers_to_save.append(new_answer)
        cit_count = len(matched["citations"])

        if cit_count >= 2:
            confidence = "High"
        elif cit_count == 1:
            confidence = "Medium"
        else:
            confidence = "Low"

        results.append({
            "question": matched["question"],
            "answer": matched["answer"],
            "citations": matched["citations"],
            "confidence": confidence
        })

    db.add_all(answers_to_save)
    db.commit()

    return {
        "questionnaire_id": questionnaire_id,
        "total_questions": len(results),
        "results": results
    }

@app.get("/questionnaire-results/{questionnaire_id}")
def get_questionnaire_results(
    questionnaire_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Fetch all questions in order
    questions = db.query(models.Question).filter(
        models.Question.questionnaire_id == questionnaire_id
    ).order_by(models.Question.order_index).all()

    if not questions:
        raise HTTPException(status_code=404, detail="No questions found")

    results = []

    for question in questions:
        # Fetch stored answer from DB
        answer = db.query(models.Answer).filter(
            models.Answer.question_id == question.id
        ).first()

        results.append({
            "question_id": question.id,
            "question": question.question_text,
            "answer": answer.answer_text if answer else None,
            "citations": answer.citations.split("\n") if answer and answer.citations else []
        })

    return {
        "questionnaire_id": questionnaire_id,
        "total_questions": len(results),
        "results": results
    }

@app.put("/update-answer/{answer_id}")
def update_answer(
    answer_id: int,
    request: UpdateAnswerRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    answer = db.query(models.Answer).filter(
        models.Answer.id == answer_id
    ).first()

    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    answer.answer_text = request.answer_text
    db.commit()

    return {"message": "Answer updated successfully"}

@app.get("/export/{questionnaire_id}")
def export_questionnaire(
    questionnaire_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    questions = db.query(models.Question).filter(
        models.Question.questionnaire_id == questionnaire_id
    ).order_by(models.Question.order_index).all()

    if not questions:
        raise HTTPException(status_code=404, detail="Questionnaire not found")

    export_content = ""

    for question in questions:
        answer = db.query(models.Answer).filter(
            models.Answer.question_id == question.id
        ).first()

        export_content += f"Question: {question.question_text}\n"

        if answer:
            export_content += f"Answer: {answer.answer_text}\n"
            if answer.citations:
                export_content += f"Citations:\n{answer.citations}\n"
        else:
            export_content += "Answer: Not generated.\n"

        export_content += "\n" + "-"*50 + "\n\n"

    file_path = f"exports/questionnaire_{questionnaire_id}.txt"
    os.makedirs("exports", exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(export_content)

    return FileResponse(
        path=file_path,
        filename=f"questionnaire_{questionnaire_id}_export.txt",
        media_type="text/plain"
    )

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/ui-login")
def ui_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })

    token = create_access_token({"sub": user.email})

    response = templates.TemplateResponse("dashboard.html", {
        "request": request,
        "token": token
    })

    response.set_cookie(key="access_token", value=token)

    return response

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )
@app.post("/ui-upload-reference")
def ui_upload_reference(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("login.html", {"request": request})

    # reuse existing logic
    return upload_reference(file=file, current_user=get_current_user_manual(token, db), db=db)


@app.post("/ui-upload-questionnaire")
def ui_upload_questionnaire(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("login.html", {"request": request})

    return upload_questionnaire(file=file, current_user=get_current_user_manual(token, db), db=db)

@app.get("/results/{questionnaire_id}", response_class=HTMLResponse)
def results_page(
    questionnaire_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    questions = db.query(models.Question).filter(
        models.Question.questionnaire_id == questionnaire_id
    ).all()

    results = []

    for q in questions:
        ans = db.query(models.Answer).filter(
            models.Answer.question_id == q.id
        ).first()

        results.append({
            "question": q.question_text,
            "answer": ans.answer_text if ans else "Not generated",
            "citations": ans.citations.split("\n") if ans else [],
            "confidence": "Medium",
            "answer_id": ans.id if ans else None
        })

    return templates.TemplateResponse(
        "results.html",
        {"request": request, "results": results}
    )

def get_current_user_manual(token: str, db: Session):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")
    return db.query(models.User).filter(models.User.email == email).first()
