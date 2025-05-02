import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.llms import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image
import base64
import io
import os
import pickle
from dotenv import load_dotenv


load_dotenv()


st.set_page_config(page_title="Whisky Finder via Image", layout="centered")

openai_api_key = os.getenv("OPENAI_API_KEY")

@st.cache_resource
def load_processed_data_with_vectors():
    with open("data/processed_data.pkl", "rb") as f:
        data = pickle.load(f)

    df = data["df"]
    descriptions = df["description_text"].fillna("")
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(descriptions)
    return df, vectorizer, tfidf_matrix

df, vectorizer, tfidf_matrix = load_processed_data_with_vectors()


chat = ChatOpenAI(
    model="gpt-4o",
    openai_api_key=openai_api_key,
   
)


def rag_from_vector(query_text, vectorizer, tfidf_matrix, df, top_k=5):
    query_vec = vectorizer.transform([query_text])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    df = df.copy()
    df["rag_score"] = scores
    return df.sort_values("rag_score", ascending=False).head(top_k)


st.title("Whisky Goggles")

uploaded_file = st.file_uploader("Upload a whisky bottle image", type=["jpg", "jpeg", "png"])

extracted_description = None

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image",  width=200)

   
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode()

    with st.spinner("🧠 Interpreting image..."):
        vision_response = chat([
            HumanMessage(
                content=[
                    {"type": "text", "text": '''The user will submit an image, and your task is to create a description based on the image to compare it with other whiskey bottles and extract it in text format as :


More Complete Description Based on the Image of Joseph Magnus Cigar Blend Bourbon:
-------------------------------------------------------------------------------

1. **Bottle Shape and Design**:
   - The bottle has an **elegant, curved shape**, with a unique long neck that tapers slightly towards the top. The base of the bottle has a broad and sturdy design.
   - The **clear glass** allows the rich amber color of the bourbon to be seen clearly, hinting at the aging process and the depth of the whiskey.

2. **Cap**:
   - The cap is a **wooden top** with a **golden band** around it, giving it a premium, artisanal look.
   - A **metal band** is visible around the neck of the bottle, engraved with the words **"REMARKABLE SPIRIT"**, further enhancing the luxury feel.

3. **Label and Text**:
   - The label prominently features **"Joseph Magnus"** in **elegant script** at the top, followed by **"Cigar Blend Bourbon"** in a bold, vintage font, signifying the unique blend of this whiskey.
   - **"Straight Bourbon Whiskey"** is stated on the label, highlighting the authenticity of the product, along with **"Finished in Amaron, Sherry, and Cognac Casks"**, revealing the complex maturation process.
   - **Batch number and signature** are printed on the label, adding a personalized touch to the bottle.
   
4. **Color Scheme**:
   - The label employs a **dark brown and gold** color scheme, which gives it a vintage and luxurious appearance.
   - The **amber bourbon** inside the bottle contrasts beautifully with the golden accents on the label, enhancing its high-quality look and feel.

5. **Design Elements**:
   - The design of the label includes **ornate floral patterns**, with a vintage aesthetic that draws attention to the artisanal craftsmanship of the whiskey.
   - The **"Cigar Blend"** designation is prominently featured, signaling a unique, crafted blend perfect for cigar pairings.
   - The **wooden cap** and detailed engraving add to the bottle’s artisanal feel, positioning it as a luxury item.

-------------------------------------------------------------------------------'''},

                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                ]
            )
        ])
        extracted_description = vision_response.content.strip()



if extracted_description:

    with st.spinner("🔍 Finding similar whiskies..."):
        matches = rag_from_vector(extracted_description, vectorizer, tfidf_matrix, df)

    st.subheader("🥃 Closest Matches Based on Image")
    cols_per_row = 1  
    cols = st.columns(cols_per_row)

    for i, (_, row) in enumerate(matches.iterrows(), start=1):
    
        col = cols[i % cols_per_row]

        with col:
            st.markdown(f"""
            <div style="padding: 15px; border: 2px solid #0073e6; border-radius: 10px; box-shadow: 2px 2px 12px rgba(0, 0, 0, 0.1); margin-bottom: 15px; text-align: center;">
                <h4 style="color: #0073e6;">{i}. {row['name']}</h4>
                <div>
                    <img src="{row['image_url']}" alt="whisky image" width="150" style="border-radius: 10px;">
                </div>
                <ul style="list-style-type: none; padding: 0; color: #333; text-align: left;">
                    <li><strong>🏭 Distillery:</strong> {row.get('Distillery', 'N/A')}</li>
                    <li><strong>📍 Region:</strong> {row.get('Region', 'N/A')}</li>
                    <li><strong>💲 MSRP:</strong> ${row.get('avg_msrp', 'N/A')}</li>
                    <li><strong>🔍 Similarity Score:</strong> {row['rag_score']:.2f}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
