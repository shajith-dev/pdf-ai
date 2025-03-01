import uuid
import hashlib
import os
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from s3 import S3Util


class LLM:
    _instance = None

    @classmethod
    def get_instance(cls, model="gpt-4o-mini", temperature=0.7):
        if cls._instance is None:
            cls._instance = ChatOpenAI(temperature=temperature, model=model)
        return cls._instance


class PDFChatSession:
    def __init__(self, object_url, model="gpt-4o-mini"):
        self.session_id = str(uuid.uuid4())
        self.object_url = object_url
        # Compute a unique vector store ID based on the object URL
        self.vectorstore_id = hashlib.md5(object_url.encode()).hexdigest()
        self.db_dir = f"vector_db_{self.vectorstore_id}"
        self.context = self._extract_text()
        self.vectorstore = self._create_vectorstore()
        self.llm = LLM.get_instance(model=model)
        self.memory = ConversationBufferMemory(
            memory_key='chat_history', return_messages=True)
        self.conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(),
            memory=self.memory
        )

    def _extract_text(self):
        util = S3Util()
        return util.get_pdf_text(self.object_url)

    def _create_vectorstore(self):
        # Create a Document from the PDF text and include metadata
        doc = Document(page_content=self.context, metadata={
                       "pdf_id": self.vectorstore_id})
        text_splitter = CharacterTextSplitter(
            separator=" ", chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents([doc])
        embeddings = OpenAIEmbeddings()

        # If the persist directory exists and is non-empty, load the existing vector store.
        if os.path.exists(self.db_dir) and os.listdir(self.db_dir):
            vectorstore = Chroma(persist_directory=self.db_dir,
                                 embedding_function=embeddings)
        else:
            # Otherwise, create a new vector store and persist it.
            vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=self.db_dir
            )
        return vectorstore

    def chat(self, message):
        result = self.conversation_chain.invoke({"question": message})
        return result["answer"]
