To Run the Application

Backend:                                                                                                                                                                 
cd src/service                                                                                                                                                           
python -m venv venv                                                                                                                                                      
source venv/bin/activate  # On Windows: venv\Scripts\activate                                                                                                            
pip install -r requirements.txt                                                                                                                                          
cp .env.example .env  # Edit .env to add your Claude API key                                                                                                             
uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs

Frontend:                                                                                                                                                                
cd src/frontend                                                                                                                                                          
npm install                                                                                                                                                              
npm run dev
# App at http://localhost:5173