from bs4 import BeautifulSoup
import warnings
from bs4 import MarkupResemblesLocatorWarning

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

def parse_quiz(html_content: str):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Dummy parser example: extract all inputs with id
    questions = []
    for inp in soup.find_all("input"):
        qid = inp.get("id")
        if qid:
            questions.append({"id": qid})
    return questions
