from agents.googleDocs_llm import googleDocs_openAI

async def workflow(user_input,agent):

    redditResearch = await agent.invoke(user_input, googleDocs_openAI, "reddit")

    googleDocsPrompt = redditResearch + "\nThis is the info based on user research\n"


    googleDocsResponse = await agent.invoke(googleDocsPrompt, googleDocs_openAI, "googleDocs")

    revisedText = f'''

The user request's strategy: {user_input}

The inital reddit research : {redditResearch}

The content drafted: {googleDocsResponse}

Based on this I need to know if the content aligns with the user's request and if not,
do a revised research and pull reddit posts more relevant to the user's request.

After the research do not forget to send back the google docs's ID along with your response.
It is important to call another agent to edit the doc.

'''
    

    revisedResearch = await agent.invoke(revisedText, googleDocs_openAI, "reddit")


    docsFinalPrompt = revisedResearch + "\nYou have the google docs ID so you are gonna write it to the same doc.\n"


    googleDocsFinalResponse = await agent.invoke(docsFinalPrompt, googleDocs_openAI, "googleDocs")

    
    return googleDocsFinalResponse

