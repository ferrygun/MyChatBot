from flask import Flask, request, jsonify
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain, ConversationChain
from langchain.prompts import PromptTemplate
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ChatVectorDBChain
from langchain.chat_models import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
import json
import os

os.environ["OPENAI_API_TYPE"] = "azure"
os.environ["OPENAI_API_VERSION"] = ""
os.environ["OPENAI_API_BASE"] = ""
os.environ["OPENAI_API_KEY"] = ""

app = Flask(__name__)

'''
{
    "userMessage": {
        "user_id": "A15",
        "question": "I will be taking leave from Oct 18 to 25"
    }
}
'''

# Human: I need to apply for my annual leave. How can I do that?
# Bot: When will you be going on leave?
# Human: I will be taking leave from Oct 18 to 25
# Bot: Which country will you be going to?
# Human: I will be going to Indonesia
# Bot: Do you need a visa letter for your travel?
# Human: Yes I need that
# Bot: Do you need help to setup an out of office message for your leave period?
# Human: No I dont need that
# Bot: Do you need to delegate your approvals to someone else during your leave period?
# Human: Yes please delegate

# I will be going on leave from Sept 2 to 3, I am going to Indonesia and I dont need a visa letter. I need help to setup an out of office message and delegate approval to Superman
'''
{
    "answer": "Understood, you would like to delegate your approvals during your leave period. Thank you for providing all the necessary information. I will proceed with the next steps.",
    "country_ID": "ID",
    "delegate": "y",
    "follow_a": "N/A",
    "fromDate": "18/10/2022",
    "intent": "leave",
    "setup_office": "n",
    "toDate": "25/10/2022",
    "visa_letter": "y"
}
'''

class Session:
    def __init__(self):
        self.embedding_model = OpenAIEmbeddings(chunk_size=10)
        self.recipe_1 = TextLoader('FD.txt').load()
        self.text_splitter_1 = CharacterTextSplitter(chunk_overlap=100)
        self.recipe_1_content = self.text_splitter_1.split_documents(self.recipe_1)

        self.faiss_db = FAISS.from_documents(self.recipe_1_content, self.embedding_model)  

        self.retriever = self.faiss_db.as_retriever(search_type="similarity", search_kwargs={"k": 4})

        self.llm = AzureChatOpenAI(
            temperature=0,
            deployment_name="gpt-4",
        )

        self.memory = ConversationBufferMemory(memory_key="chat_history", input_key="question", return_messages=True, output_key="answer")

        self.prompt_template = """
        You are a helpful support chatbot having a conversation with a human.
        Follow exactly these steps:
        1. Read and examine the context below CAREFULLY.
        2. Answer the question using only the context information

        User Question: 
        {question}

        Context: 
        {context}

        Chat History: 
        {chat_history}


        Please note the following carefully:
        - You need to get the country name, if user didn't specify, please ask.
        - You NEED TO GET ALL follow up actions (follow_a) mentioned in the context answered by user. If not, KEEP asking user. DO NOT ask other questions. 
        - Get the user leave dates and capture it in the fromDate and toDate. You need to get from and to date when the user will be leave, if you don't have this info, clarify with user.
        - if user needs a visa letter, capture that information in the visa_letter.
        - if user needs help to setup an out of office message, capture that information in the setup_office.
        - if user needs help to delegate their approval to Superman, capture that information in the delegate.
        - If you got all information you need, reply user with thanks I got all information I need and will proceed with next steps. Proceed to clear the chat_history
        - If you don't know the answer, just say you don't know. Do NOT try to make up an answer. If the question is not related to the context, politely respond that you are tuned to only answer questions that are related to the context. Use as much detail as possible when responding.
        - DO NOT reply with this: I'm sorry, but as a chatbot, I don't have personal plans or intentions.

        Reply in JSON format with the following information:
        answer, your answer should also mention the follow up action if any (ask one at a time) (i.e. answer)
        country ID (i.e. country_ID: ID for Indonesia, JP for Japan)  
        intent (i.e. intent: leave)
        follow up action from the chatbot to human if any, reply one at a time, if not just reply with N/A (ie. follow_a)
        user leaves date from and to: (ie. fromDate, toDate) in this format DD/MM/YYYY. Both date from and to should be populated, if not ask user. if to date is lesser than from date, clarify with user.
        visa letter (ie. visa_letter: y or n)
        need to setup office (ie. setup_office: y or n)
        delegate their approval to Superman (ie. delegate: y or n)
        """

        self.QA_PROMPT = PromptTemplate(
            template=self.prompt_template, input_variables=['context', 'question', 'chat_history']
        )

        self.qa = ConversationalRetrievalChain.from_llm(llm=self.llm, 
                                                       chain_type="stuff",
                                                       retriever=self.retriever, 
                                                       memory=self.memory, 
                                                       combine_docs_chain_kwargs={"prompt": self.QA_PROMPT},
                                                       verbose=False)

        self.chat_history = []
        self.first_iteration = True

sessions = {}

@app.route('/greet', methods=['GET'])
def greet():
    return jsonify({'message': 'Hi, I am the Tango Bot!'})

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    print(data)

    #remove this
    data = data["userMessage"]
    #print(data)

    user_id = data.get('user_id', None)
    if user_id is None:
        return jsonify({'error': 'user_id is required'}), 400
    
    if user_id not in sessions:
        sessions[user_id] = Session()

    session = sessions[user_id]

    question = data.get('question', None)
    if question is None:
        return jsonify({'error': 'question is required'}), 400

    chat_history = session.chat_history
    result = session.qa({"question": question, "chat_history": chat_history})
    if not session.first_iteration:
        result = session.qa({"question": question, "chat_history": chat_history})

    chat_history.append((question, result["answer"]))
    session.chat_history = chat_history

    session.first_iteration = False

    parsed_data = json.loads(result["answer"])
    

    response_data = {
        "answer": parsed_data["answer"],
        "country_ID": parsed_data["country_ID"],
        "intent": parsed_data["intent"],
        "follow_a": parsed_data["follow_a"],
        "fromDate": parsed_data["fromDate"],
        "toDate": parsed_data["toDate"],
        "visa_letter": parsed_data["visa_letter"],
        "setup_office": parsed_data["setup_office"],
        "delegate": parsed_data["delegate"]
    }

    return jsonify(response_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
