
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import inch

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(SCRIPT_DIR, 'pdfs')
SHARED_DIR = os.path.join(PDF_DIR, 'shared')
USER1_DIR = os.path.join(PDF_DIR, 'user1')
USER2_DIR = os.path.join(PDF_DIR, 'user2')

# --- Content for PDFs ---
CONTENT = {
    "shared_file_1": {
        "title": "The Future of Artificial Intelligence",
        "pages": [
            "Page 1: Introduction to AI. Artificial Intelligence is a branch of computer science that aims to create intelligent machines. It has become an essential part of the technology industry. Research in AI is concerned with producing machines to automate tasks requiring intelligent behavior.",
            "Page 2: Machine Learning and Deep Learning. Machine Learning is a subset of AI that allows systems to learn and improve from experience without being explicitly programmed. Deep Learning is a further subset of Machine Learning that uses neural networks with many layers to analyze various factors in data.",
            "Page 3: AI in Everyday Life. AI is already all around us, from virtual assistants like Siri and Alexa to recommendation engines on Netflix and Amazon. It is also used in healthcare for diagnosing diseases and in finance for fraud detection. The potential applications of AI are vast and continue to grow."
        ]
    },
    "shared_file_2": {
        "title": "Introduction to Python Programming",
        "pages": [
            "Page 1: Why Python? Python is a high-level, interpreted programming language known for its simple syntax and readability. It is widely used in web development, data science, artificial intelligence, and scientific computing. Its large standard library provides tools suited to many tasks.",
            "Page 2: Basic Syntax. Python's syntax is designed to be clean and easy to read. It uses indentation to define code blocks, rather than braces or keywords. Common data types include integers, floats, strings, and booleans. Variables are created when you assign a value to them.",
            "Page 3: Libraries and Frameworks. Python's power comes from its extensive ecosystem of libraries and frameworks. For web development, Django and Flask are popular choices. For data science, libraries like NumPy, Pandas, and Matplotlib are essential. For AI, there is TensorFlow and PyTorch."
        ]
    },
    "user1_file_1": {
        "title": "Advanced Concepts in Computer Vision",
        "pages": [
            "Page 1: What is Computer Vision? Computer Vision is a field of AI that enables computers to interpret and understand the visual world. Using digital images from cameras and videos, machines can identify and classify objects, and then react to what they 'see.'",
            "Page 2: Object Detection. Object detection is a key task in computer vision where the goal is to find instances of objects in images. Popular algorithms include YOLO (You Only Look Once) and R-CNN (Region-based Convolutional Neural Networks). These are used in autonomous driving and surveillance.",
            "Page 3: Image Segmentation. Image segmentation goes beyond object detection by classifying each pixel of an image. This allows for a more granular understanding of the scene. Techniques include semantic segmentation and instance segmentation, used in medical imaging and satellite imagery analysis."
        ]
    },
    "user1_file_2": {
        "title": "The Principles of Robotics",
        "pages": [
            "Page 1: Introduction to Robotics. Robotics is an interdisciplinary branch of engineering and science that includes mechanical engineering, electrical engineering, computer science, and others. Robotics deals with the design, construction, operation, and use of robots.",
            "Page 2: Components of a Robot. A typical robot has a movable physical structure, a motor of some sort, a sensor system, a power supply and a computer 'brain' that controls all of these elements. Robots can be autonomous, semi-autonomous, or remotely controlled.",
            "Page 3: Applications of Robotics. Robots are used in many industries. In manufacturing, they perform repetitive tasks with high precision. In healthcare, they assist in surgeries. In logistics, they automate warehouses. Exploration robots are sent to dangerous environments like space or the deep sea."
        ]
    },
    "user2_file_1": {
        "title": "A Guide to Data Science",
        "pages": [
            "Page 1: The Data Science Lifecycle. Data science is the process of extracting knowledge and insights from data. The lifecycle typically involves data collection, data cleaning, exploratory data analysis, modeling, and interpretation of results. It's an iterative process.",
            "Page 2: Key Skills for a Data Scientist. A data scientist needs a blend of skills, including programming (Python or R), statistics, machine learning, data visualization, and domain knowledge. Communication skills are also critical to explain findings to stakeholders.",
            "Page 3: Impact of Data Science. Data science is transforming industries. It helps businesses make better decisions, enables personalized customer experiences, and drives innovation in fields like genetics and astronomy. It is the key to unlocking the value hidden in data."
        ]
    },
    "user2_file_2": {
        "title": "Fundamentals of Business Analytics",
        "pages": [
            "Page 1: What is Business Analytics? Business Analytics refers to the skills, technologies, and practices for continuous iterative exploration and investigation of past business performance to gain insight and drive business planning. It focuses on developing new insights from data.",
            "Page 2: Types of Analytics. There are three main types of analytics. Descriptive analytics, which tells you what happened in the past. Predictive analytics, which forecasts what might happen in the future. And prescriptive analytics, which recommends actions you can take to affect desired outcomes.",
            "Page 3: Tools and Techniques. Common tools for business analytics include Microsoft Excel, Tableau for visualization, and SQL for data querying. Statistical techniques like regression analysis and forecasting are also widely used to understand trends and make predictions."
        ]
    }
}

# --- Helper Function to Create a PDF ---
def create_pdf(file_path, title, pages):
    """Creates a multi-page PDF with the given title and content."""
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    styles = getSampleStyleSheet()
    style = styles['Normal']
    
    for page_num, page_content in enumerate(pages):
        # Page Title
        c.setFont('Helvetica-Bold', 16)
        c.drawCentredString(width / 2.0, height - 0.75 * inch, title)
        
        # Page Number
        c.setFont('Helvetica', 10)
        c.drawString(inch, 0.75 * inch, f"Page {page_num + 1}")
        
        # Page Content
        p = Paragraph(page_content, style)
        p.wrapOn(c, width - 2 * inch, height - 2 * inch)
        p.drawOn(c, inch, height - 1.75 * inch)
        
        c.showPage()
        
    c.save()
    print(f"Created PDF: {os.path.basename(file_path)}")

# --- Main Script ---
if __name__ == "__main__":
    print("Starting PDF generation...")
    # Create directories if they don't exist
    os.makedirs(SHARED_DIR, exist_ok=True)
    os.makedirs(USER1_DIR, exist_ok=True)
    os.makedirs(USER2_DIR, exist_ok=True)

    # Create shared PDFs
    create_pdf(os.path.join(SHARED_DIR, "shared_file_1.pdf"), CONTENT["shared_file_1"]["title"], CONTENT["shared_file_1"]["pages"])
    create_pdf(os.path.join(SHARED_DIR, "shared_file_2.pdf"), CONTENT["shared_file_2"]["title"], CONTENT["shared_file_2"]["pages"])

    # Create user1 PDFs
    create_pdf(os.path.join(USER1_DIR, "user1_file_1.pdf"), CONTENT["user1_file_1"]["title"], CONTENT["user1_file_1"]["pages"])
    create_pdf(os.path.join(USER1_DIR, "user1_file_2.pdf"), CONTENT["user1_file_2"]["title"], CONTENT["user1_file_2"]["pages"])

    # Create user2 PDFs
    create_pdf(os.path.join(USER2_DIR, "user2_file_1.pdf"), CONTENT["user2_file_1"]["title"], CONTENT["user2_file_1"]["pages"])
    create_pdf(os.path.join(USER2_DIR, "user2_file_2.pdf"), CONTENT["user2_file_2"]["title"], CONTENT["user2_file_2"]["pages"])

    print("\nPDF generation complete.")
    print(f"Files are located in: {PDF_DIR}")
