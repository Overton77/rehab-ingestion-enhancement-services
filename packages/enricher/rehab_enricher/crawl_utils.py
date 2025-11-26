from crawl4ai import AsyncWebCrawler  



async def return_markdown(url: str) -> str:  
    try: 
        async with AsyncWebCrawler() as crawler:  
            result = await crawler.arun( 
            url=url, 
        ) 

            return result.markdown 
    except Exception as e: 
        raise e  

