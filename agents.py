from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

class SocialMediaAgents:
    PLATFORM_LIMITS = {
        "twitter": {"chars": 280, "words": None},
        "instagram": {"chars": None, "words": 400},
        "linkedin": {"chars": None, "words": 600},
        "facebook": {"chars": None, "words": 1000}
    }

    def __init__(self, api_key: str):
        """Initialize the agent with a Google API key."""
        self.llm = GoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)

    def _create_chain(self, template: str) -> LLMChain:
        """Create an LLM chain with the given prompt template."""
        prompt = ChatPromptTemplate.from_template(template)
        return LLMChain(llm=self.llm, prompt=prompt)

    def _enforce_limits(self, text: str, platform: str) -> str:
        """Enforce platform-specific character or word limits."""
        limits = self.PLATFORM_LIMITS[platform.lower()]
        if limits["chars"] and len(text) > limits["chars"]:
            return text[:limits["chars"]-3] + "..."
        if limits["words"]:
            words = text.split()
            if len(words) > limits["words"]:
                return " ".join(words[:limits["words"]]) + "..."
        return text

    # def twitter_transform(self, title: str, description: str) -> dict:
    #     """Transform content for Twitter."""
    #     link = "https://www.eye-on.ai/podcast-archive"
    #     template = """Transform this into a Twitter post (280 characters max):
    #     - Attention-grabbing message
    #     - 1-2 relevant hashtags
    #     - Essential information only
        
    #     Format output EXACTLY like this:
    #     New Title: [transformed title]
    #     ---
    #     New Description: [transformed description]
        
    #     add this line after descripttion and make link clickable listen to full podcast on {link}

    #     Original Content:
    #     Title: {title}
    #     Description: {description}"""
    #     chain = self._create_chain(template)
    #     response = chain.invoke({"title": title, "description": description, "link": link})

    def twitter_transform(self, title: str, description: str,link:str) -> dict:
        """Transform content for Twitter with a clickable link and within 280 characters."""
        template = """
        Transform this into a Twitter post (max 280 characters total):
        - Create an attention-grabbing single-line tweet using key info from the title and description
        - Include 1-2 relevant hashtags
        - End with this line exactly: Listen to full podcast: {link}
        - Ensure the ENTIRE result is no more than 280 characters TOTAL (including the link line)
        - if character more than 280 characters manage limit and exclude description character
        - Don't short {link} i want full link
        Return in this format:
        New Title: [transformed title]
        ---
        New Description: [tweet content]

        Original Content:
        Title: {title}
        Description: {description}
            """
        chain = self._create_chain(template)
        response = chain.invoke({"title": title, "description": description, "link": link})
        


        parts = response['text'].split('---')
        result = {
            "new_title": parts[0].replace('New Title:', '').strip(),
            "new_description": parts[1].replace('New Description:', '').strip()
        }
        combined_text = f"{result['new_title']} {result['new_description']}"
        limited_text = self._enforce_limits(combined_text, "twitter")
        if len(limited_text) < len(combined_text):
            result['new_title'] = ""
            result['new_description'] = limited_text
        return result

    def instagram_transform(self, title: str, description: str) -> dict:
        """Transform content for Instagram."""
        template = """Transform this into an Instagram post (400 words max):
        - Catchy title with relevant emojis
        - Engaging description
        - 3-5 relevant hashtags
        
        Format output EXACTLY like this:
        New Title: [transformed title]
        ---
        New Description: [transformed description]
        
        Original Content:
        Title: {title}
        Description: {description}"""
        chain = self._create_chain(template)
        response = chain.invoke({"title": title, "description": description})
        parts = response['text'].split('---')
        result = {
            "new_title": parts[0].replace('New Title:', '').strip(),
            "new_description": parts[1].replace('New Description:', '').strip()
        }
        result['new_description'] = self._enforce_limits(result['new_description'], "instagram")
        return result

    def linkedin_transform(self, title: str, description: str,link:str) -> dict:
        """Transform content for Linkedin with a clickable link and within 550 words."""
        template = """Transform this into a LinkedIn post (550 words max):
        - Professional title
        - Detailed description with business insights
        - 2-3 relevant hashtags
        - Professional tone
        - End with this line exactly: Listen to full podcast: {link}
        - Don't change link format and words.
        - Ensure the ENTIRE result is no more than 550 words TOTAL (including the link line)
        - if character more than 550 words manage limit and exclude description character
        - Don't short {link} i want full link
        
        Format output EXACTLY like this:
        New Title: [transformed title]
        ---
        New Description: [transformed description]
        
        Original Content:
        Title: {title}
        Description: {description}
        """
        chain = self._create_chain(template)
        response = chain.invoke({"title": title, "description": description,"link": link})
        parts = response['text'].split('---')
        result = {
            "new_title": parts[0].replace('New Title:', '').strip(),
            "new_description": parts[1].replace('New Description:', '').strip()
        }
        result['new_description'] = self._enforce_limits(result['new_description'], "linkedin")
        return result

    def facebook_transform(self, title: str, description: str) -> dict:
        """Transform content for Facebook."""
        template = """Transform this into a Facebook post (1000 words max):
        - Engaging title
        - Conversational description
        - Call to action for engagement
        - 1-2 relevant hashtags
        
        Format output EXACTLY like this:
        New Title: [transformed title]
        ---
        New Description: [transformed description]
        
        Original Content:
        Title: {title}
        Description: {description}"""
        chain = self._create_chain(template)
        response = chain.invoke({"title": title, "description": description})
        parts = response['text'].split('---')
        result = {
            "new_title": parts[0].replace('New Title:', '').strip(),
            "new_description": parts[1].replace('New Description:', '').strip()
        }
        result['new_description'] = self._enforce_limits(result['new_description'], "facebook")
        return result