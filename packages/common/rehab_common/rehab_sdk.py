import asyncio  
from dotenv import load_dotenv 
from pathlib import Path   
import os  
from graphql_client.client import RehabApiClient   
from graphql_client.input_types import CreateProspectiveRehabInput  
from graphql_client.exceptions import GraphQLClientError  
from typing import Optional, List


here = Path(__file__).parent.parent  
load_dotenv(dotenv_path=here / ".env")



GRAPHQL_ENDPOINT = os.getenv("GRAPHQL_ENDPOINT") or "http://localhost:3000/graphql"

graphql_client = RehabApiClient(GRAPHQL_ENDPOINT) 



async def batch_create_rehabs(data: List[CreateProspectiveRehabInput], chunk_size: int = 100): 

    total = len(data) 
    total_successes = 0 
    total_errors = 0   
    responses = []

    for start in range(0, total, chunk_size): 
        batch = data[start:start+chunk_size] 
        print(f"Creating batch {start//chunk_size + 1} of {total//chunk_size}") 
        try: 
            resp = await graphql_client.create_many_rehabs(data=batch)  
            responses.append(resp)  
            total_successes += len(resp.create_many_rehabs) 
        except (GraphQLClientError, Exception) as e: 
            total_errors += 1 
            print(f"Error creating batch {start//chunk_size + 1}: {e}") 
            continue 

    print(f"Total successes: {total_successes}") 
    print(f"Total errors: {total_errors}") 
    print(f"Total rehabs created: {total_successes + total_errors}") 

    return  { 
        "total_successes": total_successes,
        "total_errors": total_errors,
        "responses": responses,
    }


