from phi.agent import Agent
from phi.knowledge.pdf import PDFUrlKnowledgeBase
import os
#os.environ["OPENAI_API_KEY"] = ""
from phi.vectordb.mongodb import MDBVector
db_url = ""
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
    vector_db=MDBVector(collection_name="recipes", db_url=db_url, wait_until_index_ready=60, wait_after_insert=300),
) #adjust wait_after_insert and wait_until_index_ready to your needs
knowledge_base.load(recreate=True)  
agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)
agent.print_response("How to make Thai curry?", markdown=True)
# Lets try with recreate=False
knowledge_base.load(recreate=False)  
agent = Agent(knowledge_base=knowledge_base, use_tools=True, show_tool_calls=True)
agent.print_response("How to make Thai curry?", markdown=True)

# OUTPUT
"""
INFO     Connected to MongoDB successfully.                                                                                                                                                                                                          
INFO     Using existing collection 'recipes'.                                                                                                                                                                                                        
INFO     Checking if search index 'recipes' exists.                                                                                                                                                                                                  
INFO     Dropping collection                                                                                                                                                                                                                         
INFO     Collection 'recipes' dropped successfully.                                                                                                                                                                                                  
INFO     Creating collection                                                                                                                                                                                                                         
INFO     Creating collection 'recipes'.                                                                                                                                                                                                              
INFO     Creating search index 'vector_index_1'.                                                                                                                                                                                                     
INFO     Search index 'vector_index_1' created successfully.                                                                                                                                                                                         
INFO     Loading knowledge base                                                                                                                                                                                                                      
INFO     Reading: https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf                                                                                                                                                                        
INFO     Inserting 14 documents                                                                                                                                                                                                                      
INFO     Inserted 14 documents successfully.                                                                                                                                                                                                         
INFO     Added 14 documents to knowledge base                                                                                                                                                                                                        
INFO     Search completed. Found 10 documents.                                                                                                                                                                                                       
┏━ Message ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                                                                                                                                                                   ┃
┃ How to make Thai curry?                                                                                                                                                                                                                           ┃
┃                                                                                                                                                                                                                                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
┏━ Response (7.3s) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                                                                                                                                                                   ┃
┃ Running:                                                                                                                                                                                                                                          ┃
┃                                                                                                                                                                                                                                                   ┃
┃  • search_knowledge_base(query=Thai curry recipe)                                                                                                                                                                                                 ┃
┃                                                                                                                                                                                                                                                   ┃
┃ Here's a recipe for Massaman Curry with Chicken and Potatoes, a popular type of Thai curry:                                                                                                                                                       ┃
┃                                                                                                                                                                                                                                                   ┃
┃                                                                                                          Ingredients (for two servings)                                                                                                           ┃
┃                                                                                                                                                                                                                                                   ┃
┃  • 300 grams chicken rump                                                                                                                                                                                                                         ┃
┃  • 80 grams Massaman curry paste                                                                                                                                                                                                                  ┃
┃  • 100 grams coconut cream (the top layer of coconut milk)                                                                                                                                                                                        ┃
┃  • 300 grams coconut milk                                                                                                                                                                                                                         ┃
┃  • 250 grams chicken stock                                                                                                                                                                                                                        ┃
┃  • 50 grams roasted peanuts                                                                                                                                                                                                                       ┃
┃  • 200 grams potatoes, chopped into large chunks                                                                                                                                                                                                  ┃
┃  • 100 grams onion, chopped into large chunks                                                                                                                                                                                                     ┃
┃  • 30 grams palm sugar                                                                                                                                                                                                                            ┃
┃  • 2 tbsp tamarind juice                                                                                                                                                                                                                          ┃
┃  • 1 tbsp fish sauce                                                                                                                                                                                                                              ┃
┃                                                                                                                                                                                                                                                   ┃
┃                                                                                                                    Directions                                                                                                                     ┃
┃                                                                                                                                                                                                                                                   ┃
┃  1 Simmer Coconut Cream: Simmer the coconut cream over medium heat until the oil separates. Add the Massaman curry paste and fry until the mixture darkens and becomes fragrant.                                                                  ┃
┃  2 Add Coconut Milk & Chicken: Divide the coconut milk in half. Pour the first half into the pot and continue simmering until the mix starts to dry out. Then add the chicken and the remaining coconut milk.                                     ┃
┃  3 Add Stock & Simmer: Add the chicken stock and continue simmering until it comes to a boil.                                                                                                                                                     ┃
┃  4 Add Potatoes & Peanuts: Add the roasted peanuts and potatoes. Simmer until the chicken is tender.                                                                                                                                              ┃
┃  5 Season & Cook: When the potatoes are cooked, season with fish sauce, palm sugar, and tamarind juice. Add the onion and cook through until the soup begins to dry out.                                                                          ┃
┃  6 Serve: Serve in a bowl.                                                                                                                                                                                                                        ┃
┃                                                                                                                                                                                                                                                   ┃
┃                                                                                                                       Tips                                                                                                                        ┃
┃                                                                                                                                                                                                                                                   ┃
┃  • To make tamarind juice, mix 1 part tamarind with 3 to 3.5 parts water.                                                                                                                                                                         ┃
┃  • Different brands of instant tamarind juice have varying flavors and levels of sourness.                                                                                                                                                        ┃
┃                                                                                                                                                                                                                                                   ┃
┃                                                                                                                  Health Benefits                                                                                                                  ┃
┃                                                                                                                                                                                                                                                   ┃
┃ This dish contains a variety of vitamins and minerals, including Vitamin A, B6, C, E, K, along with calcium, copper, iron, magnesium, and potassium.                                                                                              ┃
┃                                                                                                                                                                                                                                                   ┃
┃ Enjoy preparing and savoring this flavorful Thai curry!                                                                                                                                                                                           ┃
┃                                                                                                                                                                                                                                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
INFO     Creating collection                                                                                                                                                                                                                         
INFO     Using existing collection 'recipes'.                                                                                                                                                                                                        
INFO     Checking if search index 'recipes' exists.                                                                                                                                                                                                  
INFO     Loading knowledge base                                                                                                                                                                                                                      
INFO     Reading: https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf                                                                                                                                                                        
INFO     Inserting 0 documents                                                                                                                                                                                                                       
INFO     Added 0 documents to knowledge base                                                                                                                                                                                                         
INFO     Search completed. Found 10 documents.                                                                                                                                                                                                       
┏━ Message ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                                                                                                                                                                   ┃
┃ How to make Thai curry?                                                                                                                                                                                                                           ┃
┃                                                                                                                                                                                                                                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
┏━ Response (6.5s) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                                                                                                                                                                                                                                   ┃
┃ Running:                                                                                                                                                                                                                                          ┃
┃                                                                                                                                                                                                                                                   ┃
┃  • search_knowledge_base(query=How to make Thai curry)                                                                                                                                                                                            ┃
┃                                                                                                                                                                                                                                                   ┃
┃ Here's a simple recipe to make Thai Massaman Curry with Chicken and Potatoes for two servings:                                                                                                                                                    ┃
┃                                                                                                                                                                                                                                                   ┃
┃                                                                                                                   Ingredients:                                                                                                                    ┃
┃                                                                                                                                                                                                                                                   ┃
┃  • 300 grams chicken rump                                                                                                                                                                                                                         ┃
┃  • 80 grams Massaman curry paste                                                                                                                                                                                                                  ┃
┃  • 100 grams coconut cream (the top layer of coconut milk)                                                                                                                                                                                        ┃
┃  • 300 grams coconut milk                                                                                                                                                                                                                         ┃
┃  • 250 grams chicken stock                                                                                                                                                                                                                        ┃
┃  • 50 grams roasted peanuts                                                                                                                                                                                                                       ┃
┃  • 200 grams potatoes, chopped into large chunks                                                                                                                                                                                                  ┃
┃  • 100 grams onion, chopped into large chunks                                                                                                                                                                                                     ┃
┃  • 30 grams palm sugar                                                                                                                                                                                                                            ┃
┃  • 2 tbsp tamarind juice                                                                                                                                                                                                                          ┃
┃  • 1 tbsp fish sauce                                                                                                                                                                                                                              ┃
┃                                                                                                                                                                                                                                                   ┃
┃                                                                                                                    Directions:                                                                                                                    ┃
┃                                                                                                                                                                                                                                                   ┃
┃  1 Simmer Coconut Cream: In a pot, simmer the coconut cream over medium heat until the oil separates.                                                                                                                                             ┃
┃  2 Add Curry Paste: Add Massaman curry paste, and fry it until the paste darkens and becomes fragrant.                                                                                                                                            ┃
┃  3 Add Coconut Milk: Divide the coconut milk in half. Pour the first half into the pot and continue simmering until the mixture starts to dry out.                                                                                                ┃
┃  4 Cook Chicken: Add the chicken to the pot along with the remaining coconut milk.                                                                                                                                                                ┃
┃  5 Add Stock: Add chicken stock and keep simmering until it comes to a boil.                                                                                                                                                                      ┃
┃  6 Add Potatoes and Peanuts: Add roasted peanuts and potatoes, simmering until the chicken is tender.                                                                                                                                             ┃
┃  7 Season: Once the potatoes are cooked, season with fish sauce, palm sugar, and tamarind juice. Add onion and cook until the soup begins to dry out.                                                                                             ┃
┃  8 Serve: Serve the curry in a bowl.                                                                                                                                                                                                              ┃
┃                                                                                                                                                                                                                                                   ┃
┃                                                                                                                       Tips:                                                                                                                       ┃
┃                                                                                                                                                                                                                                                   ┃
┃  • To make your own tamarind juice, mix 1 portion of tamarind with 3 to 3.5 portions of water.                                                                                                                                                    ┃
┃  • Different brands of tamarind juice vary in flavor and sourness, so adjust according to taste.                                                                                                                                                  ┃
┃                                                                                                                                                                                                                                                   ┃
┃ Enjoy your Thai Massaman Curry, a flavorful and rich meal packed with spices and comfort!                                                                                                                                                         ┃
┃                                                                                                                                                                                                                                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""