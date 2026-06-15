import os

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from fastapi.responses import FileResponse

app = FastAPI()

allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Backend Running"}

@app.post("/process")
async def process(
    batch: str = Form(...),
    cgpa: float = Form(...),
    offerType: int = Form(...),
    nonBlocking: bool = Form(...),
    ctc: float = Form(...),
    # file: UploadFile = File(...)
):
    nonBlocking = str(nonBlocking).strip().lower() in {"1", "true", "yes", "on"}
    # Importing DBs
    sheet_id = "1rpfFQ2fAt4kjAl4-6qhA1lIeA933qZ5oFdzEfGXXTn0"
    gid = "0"
    if(batch=="M.Tech"):
        gid="1752743160"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    # url = "https://docs.google.com/spreadsheets/d/1rpfFQ2fAt4kjAl4-6qhA1lIeA933qZ5oFdzEfGXXTn0/edit?gid=0#gid=0"
    df = pd.read_csv(url)

    sheet_id2 = "1cLOT6_uBIZ4SzQtCQuVdkIRXgkhkavWRlqlWd1-Ack4"
    url2 = f"https://docs.google.com/spreadsheets/d/{sheet_id2}/export?format=csv&gid=0"
    # url2 = "https://docs.google.com/spreadsheets/d/1cLOT6_uBIZ4SzQtCQuVdkIRXgkhkavWRlqlWd1-Ack4/edit?gid=0#gid=0"
    sd = pd.read_csv(url2)
    # Removing Unnecessary Columns
    if(batch=="M.Tech"):
        df = df.drop(['Nationality','Permanent Address','Unnamed: 23','Academic Gaps'],axis=1,errors="ignore")
    elif(batch=="B.Tech"):
        df = df.drop(['Nationality','Permanent Address','Unnamed: 18'],axis=1,errors="ignore")
    # Keeping Filled Out Roll Number Students and their Resume Link

    df = df[df['Roll Number'].isin(sd['Roll Number'])]

    resume_map = sd.set_index('Roll Number')['Resume Link']
    df['Resume Link'] = df['Roll Number'].map(resume_map)

    sd = sd.drop(['Resume Link'],axis=1)
    df = df.merge(sd, on='Roll Number', how='left')

    # Removing Non Elligible Students
    df = df[df['Any Active Backlog?']!="Yes"]

    # Removing Non-Elligible due to CGPA
    df = df[df['CGPA (upto 2nd Semester)']>=cgpa]

    # For Intern
    if(offerType==0 or offerType==1):
        df = df[df['Blocking']!='No']
        if(nonBlocking):
            df = df[df['Non Blocking']!='No']


    # For FTE
    if(offerType==2 or offerType==3):
        df=df[df['Min Elligible CTC']<=ctc]


    # Final
    df = df.drop(['Any Active Backlog?','Min Elligible CTC','Blocking', 'Non Blocking'],axis=1)
    df.to_csv("finalDB.csv", index=False)
    return FileResponse(
        "finalDB.csv",
        media_type="text/csv",
        filename="finalDB.csv"
    )