import streamlit as st
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red

# Set up the page configuration
st.set_page_config(page_title="PDF Job Number Automation", layout="centered", page_icon="📄")

# ✅ Custom Styling for UI Enhancements
st.markdown("""
    <style>
        /* Move Logo to Top Left */
        .logo-container {
            position: absolute;
            top: 10px;
            left: 20px;
            width: 120px;
        }

        /* Center Main Content */
        .stApp { display: flex; flex-direction: column; align-items: center; }

        /* Title Styling */
        .title-container { 
            text-align: center; 
            font-weight: bold;
            color: #004aad;
            margin-top: 20px;
            margin-bottom: 20px;
        }

        /* File Upload Styling */
        .stFileUploader > div {
            border-radius: 12px;
            padding: 12px;
            background: #f4f7fc;
            border: 2px dashed #004aad;
            transition: 0.3s;
        }

        /* Input Fields */
        .stTextInput > div > div > input {
            border-radius: 8px;
            border: 1px solid #004aad;
            padding: 12px;
            background-color: white;
        }

        /* Buttons */
        .stButton > button {
            border-radius: 8px;
            font-weight: bold;
            background: linear-gradient(135deg, #004aad, #007bff);
            color: white;
            padding: 12px;
            border: none;
            transition: 0.3s;
        }

        .stButton > button:hover {
            background: linear-gradient(135deg, #003080, #0056b3);
        }

        /* Success Messages */
        .stSuccess {
            background: #e6f7ff;
            color: #004aad;
            padding: 12px;
            border-radius: 8px;
        }

        /* Download Button */
        .stDownloadButton > button {
            border-radius: 8px;
            padding: 12px;
            background: #28a745;
            color: white;
            transition: 0.3s;
        }

        .stDownloadButton > button:hover {
            background: #218838;
        }
    </style>
""", unsafe_allow_html=True)

# ✅ Logo in Top Left
col1, col2 = st.columns([0.2, 0.8])  # 20% width for logo, 80% for title
with col1:
    st.image("logo.jpg", width=120)  # Ensure "logo.jpg" is in the correct directory

# ✅ Title and Description in Right Column
with col2:
    st.title("PDF OCR Filler")
    st.markdown("Upload your PDFs, enter a job number, and download the modified files.")

# ✅ File uploader
uploaded_files = st.file_uploader("📂 Upload PDFs", type=["pdf"], accept_multiple_files=True)

# ✅ Job number input
job_number = st.text_input("🔢 Enter Job Number", placeholder="E.g., EISPL / 14297 / SEA")

# ✅ Session State to Store Processed PDFs (Prevents Refresh Issues)
if "processed_pdfs" not in st.session_state:
    st.session_state.processed_pdfs = []
if "processed_filenames" not in st.session_state:
    st.session_state.processed_filenames = []
if "processed_ready" not in st.session_state:
    st.session_state.processed_ready = False

def add_job_number_to_pdf(input_pdf, job_number):
    """
    Adds a job number at the exact top center of the first page of a PDF.
    - Handles all rotation cases (0°, 90°, 180°, 270°).
    - Ensures the text is never upside down.
    - Uses bold red text for maximum visibility.
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    first_page = reader.pages[0]
    rotation = first_page.get("/Rotate") or 0
    width = float(first_page.mediabox.width)
    height = float(first_page.mediabox.height)

    # ✅ Create a new PDF Overlay
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    can.setFont("Helvetica-Bold", 18)
    can.setFillColor(red)

    # ✅ Ensure Text is Always Horizontal and at the Top Center
    text_width = can.stringWidth(job_number, "Helvetica-Bold", 18)
    x_position = (width - text_width) / 2
    y_position = height - 30

    if rotation == 90:
        can.translate(width, 0)
        can.rotate(90)
        x_position, y_position = (height - text_width) / 2, width - 30
    elif rotation == 270:
        can.translate(0, height)
        can.rotate(-90)
        x_position, y_position = (height - text_width) / 2, 30
    elif rotation == 180:
        can.translate(width, height)
        can.rotate(180)
        x_position, y_position = (width - text_width) / 2, 50

    can.drawString(x_position, y_position, job_number)
    can.save()

    # ✅ Merge the Overlay with the Original PDF
    packet.seek(0)
    new_pdf = PdfReader(packet)
    first_page.merge_page(new_pdf.pages[0])  
    writer.add_page(first_page)

    # ✅ Add Remaining Pages
    for page in reader.pages[1:]:
        writer.add_page(page)

    # ✅ Save the Modified PDF
    output_pdf = io.BytesIO()
    writer.write(output_pdf)
    output_pdf.seek(0)

    return output_pdf

# ✅ Process PDFs and Store Outputs for Merging
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

# ✅ Display Download Buttons Without Page Refresh
if st.session_state.get("processed_ready", False):
    for pdf, filename in zip(st.session_state.processed_pdfs, st.session_state.processed_filenames):
        st.download_button(label=f"📥 Download {filename}", data=pdf, file_name=filename, mime="application/pdf")

    if len(st.session_state.processed_pdfs) > 1:
        merged_pdf_writer = PdfWriter()
        for pdf in st.session_state.processed_pdfs:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                merged_pdf_writer.add_page(page)
        
        merged_pdf_output = io.BytesIO()
        merged_pdf_writer.write(merged_pdf_output)
        merged_pdf_output.seek(0)
        st.download_button(label="📥 Download Merged PDF", data=merged_pdf_output, file_name="merged_output.pdf", mime="application/pdf")

# ✅ Refresh Button
if st.button("🔄 Refresh"):
    st.session_state.processed_pdfs = []
    st.session_state.processed_filenames = []
    st.session_state.processed_ready = False
    st.success("🔄 Ready for new entries!")



