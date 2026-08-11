import os
import re
import requests
import zipfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from fastapi.responses import FileResponse

app = FastAPI()

# allowed_origins = [
#     origin.strip()
#     for origin in os.getenv("FRONTEND_ORIGINS", "https://nitd2027db.vercel.app").split(",")
#     if origin.strip()
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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

    sd = sd.drop_duplicates(subset="Roll Number")
    resume_map = sd.set_index('Roll Number')['Resume Link']
    df['Resume Link'] = df['Roll Number'].map(resume_map)

    sd = sd.drop(['Resume Link'],axis=1)
    df = df.merge(sd, on='Roll Number', how='left')

    # Removing Non Elligible Students
    df = df[df['Any Active Backlog?']!="Yes"]

    # Removing Non-Elligible due to CGPA
    if(batch=="B.Tech"):
        df = df[df['CGPA (upto 6th Semester)']>=cgpa]
    elif(batch=="M.Tech"):
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


def extract_file_id(url):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)

    if match:
        return match.group(1)

    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)

    if match:
        return match.group(1)

    return None


def download_resumes(df):
    os.makedirs("resumes", exist_ok=True)

    for _, row in df.iterrows():

        roll_number = str(row["Roll Number"]).strip()
        name = str(row["Name"]).strip()
        url = str(row["Resume Link"]).strip()

        file_id = extract_file_id(url)

        if not file_id:
            print(f"Invalid Google Drive URL: {url}")
            continue

        download_url = (
            f"https://drive.usercontent.google.com/download"
            f"?id={file_id}&export=download&confirm=t"
        )

        filename = f"{roll_number} {name}.pdf"
        filepath = os.path.join("resumes", filename)

        response = requests.get(download_url)

        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)

            print(f"Downloaded: {filename}")

        else:
            print(f"Failed: {filename} | Status: {response.status_code}")

def create_zip():
    zip_path = "resumes.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:

        for filename in os.listdir("resumes"):
            filepath = os.path.join("resumes", filename)

            if os.path.isfile(filepath):
                zip_file.write(filepath, arcname=filename)

    return zip_path


@app.get("/resume")
def resume():
    # Fetching URL
    # url = https://docs.google.com/spreadsheets/d/1cLOT6_uBIZ4SzQtCQuVdkIRXgkhkavWRlqlWd1-Ack4/edit?gid=1871555081#gid=1871555081
    sheetId = "1cLOT6_uBIZ4SzQtCQuVdkIRXgkhkavWRlqlWd1-Ack4"
    gId = "1871555081"
    url = f"https://docs.google.com/spreadsheets/d/{sheetId}/export?format=csv&gid={gId}"
    
    # Fetching Dataframe
    df = pd.read_csv(url)
    
    # Calling to download DF
    download_resumes(df)
    zip_path = create_zip()
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="resumes.zip"
    )

    
    
