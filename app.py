import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import csv
import datetime

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Global variable to track whether CSV file has been created during the current session
csv_file_created = False

def get_pdf(pdf_folder):
    text = ""
    for pdf_file in os.listdir(pdf_folder):
        if pdf_file.endswith(".pdf"):
            pdf_path = os.path.join(pdf_folder, pdf_file)
            pdf_reader = PdfReader(pdf_path)
            for page in pdf_reader.pages:
                text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model='models/embedding-001')
    vector_stores = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_stores.save_local('faiss_index')

def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not in
    provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """
    model = ChatGoogleGenerativeAI(model='gemini-pro', temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=['context', 'question'])
    chain = load_qa_chain(model, chain_type='stuff', prompt=prompt)
    return chain

def save_to_csv(question, answer, csv_file_path='responses.csv'):
    global csv_file_created

    if not csv_file_created:
        os.makedirs('responses', exist_ok=True)
        csv_file_path = os.path.join('responses', csv_file_path)

        with open(csv_file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            if os.path.getsize(csv_file_path) == 0:
                writer.writerow(['Question', 'Answer'])  # Write header only if the file is new

        csv_file_created = True  # Set the flag to True after creating the CSV file

    with open(csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([question, answer])

def main():
    st.set_page_config("Chat with PDF using Gemini💁")
    st.title("Chat with PDF using Gemini💁")

    pdf_folder = "/Users/aayushaggarwal/Desktop/Gemini_internship/pdf_folder"  # Update this with the path to your PDF folder

    user_question = st.text_input("Ask a Question from the PDF Files")

    if st.button("Get Reply"):
        raw_text = get_pdf(pdf_folder)
        text_chunks = get_text_chunks(raw_text)
        get_vector_store(text_chunks)

        embeddings = GoogleGenerativeAIEmbeddings(model='models/embedding-001')
        new_db = FAISS.load_local('faiss_index', embeddings)
        docs = new_db.similarity_search(user_question)

        chain = get_conversational_chain()
        response = chain(
            {'input_documents': docs, 'question': user_question},
            return_only_outputs=True
        )

        save_to_csv(user_question, response['output_text'])

        st.write('Reply:', response['output_text'])

if __name__ == "__main__":
    main()
