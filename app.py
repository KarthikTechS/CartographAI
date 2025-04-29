from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import json
from datetime import datetime
import os
from fpdf import FPDF
import requests
import json

app = FastAPI()

# Load prompts from JSON file
with open('prompts.json', 'r') as f:
    PROMPTS = json.load(f)

class DBMLInput(BaseModel):
    dbml_inputs: List[str]

class SQLInput(BaseModel):
    sql_input: str

def format_explanation(explanation):
    lines = explanation.split('\n')
    formatted_lines = []

    for line in lines:
        line = line.replace('**', '').replace('*', '').strip()

        if line.startswith('Table:'):
            formatted_lines.append(('heading', line))
        elif line.startswith('Columns:'):
            formatted_lines.append(('subheading', line))
        elif ': ' in line:
            parts = [p.strip() for p in line.split('-') if p.strip()]
            if len(parts) > 1:
                formatted_lines.append(('column', parts[0]))
                for part in parts[1:]:
                    formatted_lines.append(('property', part))
            else:
                formatted_lines.append(('text', line))
        else:
            formatted_lines.append(('text', line))

    return formatted_lines

def generate_pdf(explanations, filename="dbml_explanations.pdf"):
    # Initialize PDF with proper margins
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    
    try:
        pdf.image("Cartograph_logo.png", x=170, y=10, w=30)
    except:
        pass

    # Title with CARTOGRAPH AI and DISCOVERY
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="CARTOGRAPH AI", align='C')
    pdf.ln(8)
    pdf.set_font("Arial", 'B', size=12)
    pdf.cell(0, 10, txt="DISCOVERY", align='C')
    pdf.ln(15)

    pdf.set_font("Arial", size=11)

    for i, explanation in enumerate(explanations, 1):
        formatted = format_explanation(explanation)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, txt=f"Table {i}")
        pdf.ln(8)

        for item_type, text in formatted:
            if item_type == 'heading':
                pdf.set_font("Arial", 'B', 12)
                pdf.multi_cell(0, 6, txt=text)
                pdf.ln(4)
            elif item_type == 'subheading':
                pdf.set_font("Arial", 'B', 11)
                pdf.multi_cell(0, 6, txt=text)
                pdf.ln(2)
            elif item_type == 'column':
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(5)
                pdf.multi_cell(0, 6, txt=text)
                pdf.set_font("Arial", size=11)
                pdf.ln(1)
            elif item_type == 'property':
                pdf.cell(20)
                pdf.multi_cell(0, 6, txt=f"- {text}")
                pdf.ln(1)
            else:
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(0, 6, txt=text)
                pdf.ln(4)

        pdf.ln(8)
        if i < len(explanations):
            pdf.add_page()
            pdf.set_left_margin(15)
            pdf.set_right_margin(15)
            try:
                pdf.image("logo.png", x=170, y=10, w=30)
            except:
                pass

    pdf.output(filename)
    return filename

def get_ollama_response(messages):
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": "gemma3-12b-it",
        "messages": messages,
        "stream": False
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()['response']
    else:
        raise HTTPException(status_code=500, detail="Error generating response from Ollama")

@app.post("/generate-dbml-documentation")
async def generate_dbml_documentation(input_data: DBMLInput):
    explanations = []
    
    for dbml_input in input_data.dbml_inputs:
        messages = [
            {
                "role": "system",
                "content": PROMPTS["dbml_explanation"]["system_message"]
            },
            {
                "role": "user",
                "content": PROMPTS["dbml_explanation"]["user_template"].format(dbml_input=dbml_input)
            }
        ]
        
        explanation = get_ollama_response(messages)
        explanations.append(explanation)

    # Generate PDF
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"dbml_explanations_{timestamp}.pdf"
    pdf_path = generate_pdf(explanations, pdf_filename)
    
    return {
        "message": "Documentation generated successfully",
        "pdf_file": pdf_filename,
        "explanations": explanations
    }

@app.post("/convert-sql-to-dbml")
async def convert_sql_to_dbml(input_data: SQLInput):
    messages = [
        {
            "role": "system",
            "content": PROMPTS["sql_to_dbml"]["system_message"]
        },
        {
            "role": "user",
            "content": PROMPTS["sql_to_dbml"]["user_template"].format(sql_input=input_data.sql_input)
        }
    ]
    
    dbml_output = get_ollama_response(messages)
    
    return {
        "message": "SQL converted to DBML successfully",
        "dbml_output": dbml_output
    } 