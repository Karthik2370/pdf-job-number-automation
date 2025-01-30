import streamlit as st
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red
import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
import re
import pandas as pd

# ✅ Set Tesseract Path (Windows users)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ✅ Set up the page configuration
st.set_page_config(page_title="Logistics PDF Tool", layout="centered")

# ✅ Custom Styling
st.markdown("""
    <style>
        .main { background-color: #f4f4f4; }
        .stTextInput { border-radius: 10px; }
        .logo-container { text-align: center; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# ✅ Logo & Title Layout
col1, col2 = st.columns([0.2, 0.8])  # 20% for logo, 80% for title
with col1:
    st.image("logo.jpg", width=120)
with col2:
    st.title("📄 Logistics PDF Processor")
    st.markdown("Choose a task below to proceed.")

# ✅ Task Selection
task = st.radio("🔍 Select Task", ["BOE Data Extraction", "PDF Job Number Automation"])

# 🚀 **PDF Job Number Automation Section**
if task == "PDF Job Number Automation":
    st.subheader("📂 Upload PDFs")
    uploaded_files = st.file_uploader("Drag and drop files here", type=["pdf"], accept_multiple_files=True)
    
    job_number = st.text_input("🔢 Enter Job Number", placeholder="E.g., EISPL / 14297 / SEA")

    # ✅ Session State to Store Processed PDFs
    if "processed_pdfs" not in st.session_state:
        st.session_state.processed_pdfs = []
    if "processed_filenames" not in st.session_state:
        st.session_state.processed_filenames = []
    if "processed_ready" not in st.session_state:
        st.session_state.processed_ready = False

    def add_job_number_to_pdf(input_pdf, job_number):
        reader = PdfReader(input_pdf)
        writer = PdfWriter()
        first_page = reader.pages[0]

        rotation = first_page.get("/Rotate") or 0
        width = float(first_page.mediabox.width)
        height = float(first_page.mediabox.height)

        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(width, height))
        can.setFont("Helvetica-Bold", 18)
        can.setFillColor(red)

        if rotation == 90:
            can.translate(width, 0)
            can.rotate(90)
            text_width = can.stringWidth(job_number, "Helvetica-Bold", 18)
            x_position = (height - text_width) / 2
            y_position = width - 30
        elif rotation == 270:
            can.translate(0, height)
            can.rotate(-90)
            text_width = can.stringWidth(job_number, "Helvetica-Bold", 18)
            x_position = (height - text_width) / 2
            y_position = 30
        elif rotation == 180:
            can.translate(width, height)
            can.rotate(180)
            text_width = can.stringWidth(job_number, "Helvetica-Bold", 18)
            x_position = (width - text_width) / 2
            y_position = 50
        else:
            text_width = can.stringWidth(job_number, "Helvetica-Bold", 18)
            x_position = (width - text_width) / 2
            y_position = height - 30

        can.drawString(x_position, y_position, job_number)
        can.save()

        packet.seek(0)
        new_pdf = PdfReader(packet)
        first_page.merge_page(new_pdf.pages[0])
        writer.add_page(first_page)

        for page in reader.pages[1:]:
            writer.add_page(page)

        output_pdf = io.BytesIO()
        writer.write(output_pdf)
        output_pdf.seek(0)
        return output_pdf

    if st.button("🚀 Process PDFs"):
        if uploaded_files and job_number:
            st.session_state.processed_pdfs = []
            st.session_state.processed_filenames = []
            
            with st.spinner("⏳ Processing PDFs... Please wait!"):
                for uploaded_file in uploaded_files:
                    modified_pdf = add_job_number_to_pdf(uploaded_file, job_number)
                    st.session_state.processed_pdfs.append(modified_pdf)
                    st.session_state.processed_filenames.append(f"modified_{uploaded_file.name}")

                    st.success(f"✅ Successfully processed: {uploaded_file.name}")

            st.session_state.processed_ready = True
        else:
            st.warning("⚠️ Please upload at least one PDF and enter a job number.")

    if st.session_state.get("processed_ready", False):
        for pdf, filename in zip(st.session_state.processed_pdfs, st.session_state.processed_filenames):
            st.download_button(
                label=f"📥 Download {filename}",
                data=pdf,
                file_name=filename,
                mime="application/pdf"
            )

        if len(st.session_state.processed_pdfs) > 1:
            merged_pdf_writer = PdfWriter()
            for pdf in st.session_state.processed_pdfs:
                pdf_reader = PdfReader(pdf)
                for page in pdf_reader.pages:
                    merged_pdf_writer.add_page(page)

            merged_pdf_output = io.BytesIO()
            merged_pdf_writer.write(merged_pdf_output)
            merged_pdf_output.seek(0)

            st.success("📌 All processed PDFs have been merged into one file!")
            st.download_button(
                label="📥 Download Merged PDF",
                data=merged_pdf_output,
                file_name="merged_output.pdf",
                mime="application/pdf"
            )

    if st.button("🔄 Refresh"):
        st.session_state.processed_pdfs = []
        st.session_state.processed_filenames = []
        st.session_state.processed_ready = False
        st.success("🔄 All processed PDFs have been cleared! Ready for new entries.")

# 🚀 **BOE Data Extraction Section**
elif task == "BOE Data Extraction":
    st.subheader("📄 Upload BOE PDF")
    boe_file = st.file_uploader("📂 Upload BOE PDF", type=["pdf"])
    
    job_number_input = st.text_input("🔢 Enter Job Number for Extraction", placeholder="E.g., EISPL / 14297 / SEA")

    if boe_file and job_number_input:
        pdf_path = "uploaded_boe.pdf"
        with open(pdf_path, "wb") as f:
            f.write(boe_file.read())

        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=400)
        image_path = "boe_page1.png"
        images[0].save(image_path, "PNG")

        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
        )

        processed_image_path = "boe_page1_processed.png"
        cv2.imwrite(processed_image_path, processed)
        st.image(processed_image_path, caption="Preprocessed Image for OCR")

        extracted_text = pytesseract.image_to_string(Image.open(processed_image_path))
        st.text_area("Extracted Text from OCR", extracted_text, height=250)

        be_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", extracted_text)
        be_number = re.search(r"(\d{6,10})\s*\|\s*" + re.escape(be_date.group(1)), extracted_text) if be_date else None
        duty_amount = re.search(r"19\.TOT\. AMOUNT[^\d]*(\d+)", extracted_text)

        data = {
            "Particulars": ["IEC Code", "Importer Name", "Port Code", "BE Number", "BE Date", "Duty Amount", "Job No"],
            "Details": ["3105009540", "Eaton Industrial Systems Private Limited", "INNSA1", 
                        be_number.group(1) if be_number else "Not Found", 
                        be_date.group(1) if be_date else "Not Found", 
                        duty_amount.group(1) if duty_amount else "Not Found",
                        job_number_input]
        }

        st.table(data)
        st.download_button("📥 Download Extracted Data (CSV)", data=pd.DataFrame(data).to_csv(index=False), file_name="boe_details.csv", mime="text/csv")

