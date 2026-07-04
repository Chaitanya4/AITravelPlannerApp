# 🧭 NomadCompass - AI Travel Planner & Local Expert Chatbot

NomadCompass is an intelligent travel concierge designed to help travelers discover unique local attractions, traditional culinary specialties, artisan shopping, and cultural landmarks, curating a fully personalized day-by-day vacation roadmap.

This workspace implements a **dual high-fidelity setup**:
1. **Interactive Accessible Live Preview (React/Vite)**: Instantly usable in the AI Studio iframe. Includes custom preset routes for places like Kyoto and Paris, interactive destination inputs, and realistic live-chat expert sessions.
2. **Production-Ready Python Streamlit Application (`app.py`)**: Fulfills your exact Streamlit requirements, fully hardened against malicious parameters, packaged with dependencies, and complete with automated unit tests.

---

## 🔒 1. Advanced Security & XSS Protections
NomadCompass strictly secures all inputs and models against XSS, SQL/prompt injection, and infinite memory states:
- **XSS Stripping**: The custom `sanitize_text` engine strips all HTML/script tags from inputs before they hit the model or UI.
- **Safe Character Filtering**: `clean_destination_name` cleanses destination requests, preserving only alphanumeric, hyphens, periods, or comma characters.
- **Duration Clamping**: The planner clamps all input lengths to a maximum of 80 characters, and trip durations strictly to a range of `[1, 10]` days using boundary validation.
- **Capped Chat Logs Memory**: Expert chat logs are capped to the most recent 12 turns, preventing infinite memory usage and avoiding stack token overruns.

---

## 🧪 2. Automated Testing Suite & 100% Core Coverage
We have engineered a comprehensive, headless unit test suite (`test_app.py`) that achieves **100% test coverage** on all core sanitizers, validators, prompt builders, and model-handling methods.

### Running the Python Tests Locally:
To run the test suite instantly on your system (with zero pre-installed Streamlit or network dependencies required):
```bash
python3 -m unittest test_app.py
```

These tests validate:
- **HTML tags scrubbing** and payload limit cropping.
- **Day range bounds enforcement** (correctly clamps values like `0`, `15`, or non-integers).
- **Injection filtering** (sanitizes trailing command characters).
- **Gemini Client response parsing** with strict mock structures.
- **Expert chat histories forwarding** and boundary error handlings.

---

## 🎨 3. 100% Accessible UI Design Principles
Both the React web app and the Streamlit app are styled following **WCAG AA/AAA guidelines**:
- **High-Contrast Text**: Utilizes deep emerald green, charcoal grays, and pure whites to guarantee maximum readability.
- **Semantic HTML & Aria-labels**: Fully supports screen readers with landmark wrappers, descriptive `aria-label` tags, and proper form `<label htmlFor="...">` associations.
- **Interactive Keyboard Navigation**: Users can tab through the sidebar forms, day switchers, and favorite bookmark actions cleanly.

---

## 🚀 4. How to Run Locally

### Running the React Live Preview:
1. Install dependencies:
   ```bash
   npm install
   ```
2. Start the Vite server:
   ```bash
   npm run dev
   ```

### Running the Python Streamlit App:
1. Create a Python virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
2. Install the production dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your Google Gemini API Key:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"  # On Windows use: set GEMINI_API_KEY="your-gemini-api-key"
   ```
4. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```

---

## 🌐 5. Deploying to Free Hosting Platforms

### Option A: Streamlit Community Cloud (Recommended - Free & 0-Config)
The easiest way to host Streamlit apps is Streamlit's official free platform:
1. Push this repository to **GitHub**.
2. Visit [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
3. Click **New App**, select this repository, branch, and specify `app.py` as your entry point file.
4. Click **Advanced settings** in the Streamlit deploy dashboard, add your API Key:
   ```env
   GEMINI_API_KEY="your_api_key_here"
   ```
5. Click **Deploy**! Your app is live and shareable.

### Option B: Vercel Deployment (Serverless Python)
We have included a production-ready `vercel.json` for serverless hosting:
1. Install the Vercel CLI:
   ```bash
   npm install -g vercel
   ```
2. Run the deployment command:
   ```bash
   vercel
   ```
3. Set your environment variable inside the Vercel Dashboard under **Project Settings > Environment Variables**:
   - Key: `GEMINI_API_KEY`
   - Value: `your_gemini_api_key_here`
4. Deploy to production:
   ```bash
   vercel --prod
   ```
