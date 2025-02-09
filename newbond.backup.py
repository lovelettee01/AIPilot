#Basic 함수
import time
import json
import random
import requests
import httpx
import asyncio
from io import BytesIO
import base64
# 기존 함수들
import pandas as pd
import numpy as np 
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
#금융관련 APIs
import finnhub
import fredpy as fp
from fredapi import Fred
import yfinance as yf
from openai import OpenAI
#개인 클래스 파일 
import fredAll
#config 파일
import config
#FAST API 관련
import logging
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.responses import Response

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# FastAPI에서 정적 파일과 템플릿을 제공하기 위한 설정
templates = Jinja2Templates(directory="chartHtml")
app.mount("/static", StaticFiles(directory="chartHtml"), name="static")

# API KEY 설정
fp.api_key =config.FRED_API_KEY
fred = Fred(api_key=config.FRED_API_KEY)
finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
client = OpenAI(api_key = config.OPENAI_API_KEY)
rapidAPI = config.RAPID_API_KEY

######################################## 글로벌 주요경제지표 보여주기 Starts ###########################################
#Consumer Price Index (CPI) series data 
def CPI() -> pd.DataFrame:
    series_id = "CPIAUCSL"  
    # Fred 클래스의 get_series 메소드를 사용하여 데이터 가져오기
    df = fred.get_series(series_id=series_id)
    # df가 시리즈로 반환되므로 DataFrame으로 변환
    df = df.reset_index()
    df.columns = ['date', 'value']
    # value 컬럼을 숫자 타입으로 변환
    df['value'] = pd.to_numeric(df['value'], errors="coerce")
    # date 컬럼을 datetime 타입으로 변환 및 인덱스 설정
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index("date")
    # 12개월 전 값을 계산하여 새로운 컬럼에 할당
    df['value_last_year'] = df['value'].shift(12)
    # 연간 CPI 변화율 계산
    df['CPI(YoY)'] = (df['value'] - df['value_last_year']) / df['value_last_year'] * 100
    # 필요한 컬럼만 선택
    df = df[['CPI(YoY)']]
    return df
#Personal Consumption Expenditures (PCE) series data 
def PCE() -> pd.DataFrame:
    series_id = "PCEPI"  # PCE 시리즈 ID
    df = fred.get_series(series_id=series_id)
    df = df.reset_index()
    df.columns = ['date', 'value']
    df['value'] = pd.to_numeric(df['value'], errors="coerce")
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index("date")
    df['value_last_year'] = df['value'].shift(12)
    # 연간 PCE 변화율 계산
    df['PCE(YoY)'] = (df['value'] - df['value_last_year']) / df['value_last_year'] * 100
    df = df[['PCE(YoY)']]
    return df
#Producer Price Index (PPI) series data
def PPI() -> pd.DataFrame:
    series_id = "PPIFID"  # PPI 시리즈 ID
    df = fred.get_series(series_id=series_id)
    df = df.reset_index()
    df.columns = ['date', 'value']
    df['value'] = pd.to_numeric(df['value'], errors="coerce")
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index("date")
    df['value_last_year'] = df['value'].shift(12)
    # 연간 PPI 변화율 계산
    df['PPI(YoY)'] = (df['value'] - df['value_last_year']) / df['value_last_year'] * 100
    df = df[['PPI(YoY)']]
    return df
#Federal Funds Rate series data
def FED_RATE() -> pd.DataFrame:
    series_id = "DFEDTARU"
    df = fred.get_series(series_id=series_id)
    df = df.reset_index()
    df.columns = ['date', 'FED RATE']
    df['FED RATE'] = pd.to_numeric(df['FED RATE'], errors="coerce")
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index("date")
    df = df[['FED RATE']]
    return df
#Case-Shiller National Home Price Index series data
def CS() -> pd.DataFrame:
    series_id = "CSUSHPISA"
    df = fred.get_series(series_id=series_id)
    df = df.reset_index()
    df.columns = ['date', 'value']
    df['value'] = pd.to_numeric(df['value'], errors="coerce")
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index("date")
    # 연간 CS 변화율 계산
    df['value_last_year'] = df['value'].shift(12)
    df['CS(YoY)'] = (df['value'] - df['value_last_year']) / df['value_last_year'] * 100
    df = df[['CS(YoY)']]
    return df
#US GDP growth rate (annualized QoQ) series data
def GDP() -> pd.DataFrame:
    series_id = "A191RL1Q225SBEA"
    df = fred.get_series(series_id=series_id)
    df = df.reset_index()
    df.columns = ['date', 'GDP RATE']
    df['GDP RATE'] = pd.to_numeric(df['GDP RATE'], errors="coerce")
    # Convert 'date' column to datetime and set it as the index
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index("date")
    df = df[['GDP RATE']]
    return df

def fetch_and_merge_economic_data(start_date="2019-01-01") -> pd.DataFrame:
    # Fetch data
    cpi = CPI()
    pce = PCE()
    ppi = PPI()
    fed_rate = FED_RATE()
    cs = CS()
    gdp = GDP()
    # Merge data
    dfs = [cpi, pce, ppi, fed_rate, cs, gdp]
    # Convert to daily frequency and fill missing values with previous values
    dfs = [df.resample("D").asfreq().ffill() for df in dfs]
    # Merge data into a single DataFrame
    merged_df = pd.concat(dfs, axis=1).ffill()
    # Filter data starting from 'start_date'
    target_df = merged_df[start_date:]
    return target_df

# 경제지표들 모은것 차트로 보여주기 
def plot_economic_indicators(df: pd.DataFrame):
    fig = px.line(df, x=df.index, y=list(df.columns))
    fig.update_layout(
        title={
            'text': "Key Global Economic Indicators",
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'},
        xaxis_title="Date",
        yaxis_title="Value",
    )
    fig.show()


# 기준금리 데이터를 가져오는 함수
def get_base_rate(start_date, end_date):
    df1 = fp.series('FEDFUNDS', end_date)
    data = df1.data.loc[(df1.data.index>=start_date) & (df1.data.index<=end_date)]
    return data

# 미국채 이자율 데이터를 가져와 보여주는 함수
def create_interest_rate_chart():
    rate_10Y = fred.get_series('DGS10')
    rate_2Y  = fred.get_series('DGS2')
    #rate_3M  = fred.get_series('DGS3M')
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=rate_10Y.index, y=rate_10Y.values, mode='lines', name='10Y'))
    fig.add_trace(go.Scatter(x=rate_2Y.index,  y=rate_2Y.values,  mode='lines', name='2Y'))
#   fig.add_trace(go.Scatter(x=rate_3M.index,  y=rate_3M.values,  mode='lines', name='3M'))
    
    fig.update_layout(title='미국 국채 이자율', xaxis_title='날짜', yaxis_title='이자율(%)')
    interest_plot_html = fig.to_html(full_html=False)    
    return interest_plot_html

# 루트 경로에 대한 GET 요청 처리
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 초기 페이지 렌더링. plot_html 변수가 없으므로 비워둡니다.
    return templates.TemplateResponse("chart_pilot.html", {"request": request, "plot_html": None})

# 1번메뉴 차트요청 처리
@app.post("/submit", response_class=HTMLResponse)
async def submit(request: Request):
    plot_html = show_base_rate()
    interest_plot_html = create_interest_rate_chart()
    # 결과 페이지에 차트 HTML 포함하여 반환
    return templates.TemplateResponse("chart_pilot.html", {"request": request, "plot_html": plot_html, "interest_plot_html" :interest_plot_html})

def show_base_rate():
    start_date = '2000-01-01'
    end_date = '2023-02-01'

    # 데이터 가져오기
    data = get_base_rate(start_date, end_date)

    # 데이터 시각화
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data.values, name='기준금리'))
    fig.update_layout(title_text='미국 금리 변동 추이', title_x=0.5)
    # Plotly 차트를 HTML로 변환
    plot_html = fig.to_html(full_html=False)
    return plot_html

def finnhub_test():
    finnhub_client = finnhub.Client(api_key=config.FINNHUB_KEY)
    data = finnhub_client.bond_profile(isin='US912810TD00')
    print(data)

######################################## CALENDAR 보여주기 Starts ###########################################
# 증시 캘린더 관련 함수 
@app.post("/calendar", response_class=JSONResponse)
async def get_calendar(request: Request):
    calendar_data = await rapidapi_calendar()
    return JSONResponse(content=calendar_data)  # JSON 형식으로 데이터 반환

                        
async def rapidapi_calendar():
    url = "https://trader-calendar.p.rapidapi.com/api/calendar"
    payload = { "country": "USA", "start":"2023-12-01"}
    headers = {
	    "content-type": "application/json",
	    "X-RapidAPI-Key": rapidAPI,
	    "X-RapidAPI-Host": "trader-calendar.p.rapidapi.com"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
    calendar_data = response.json()
    return calendar_data

######################################## CALENDAR 보여주기 Ends ###########################################
######################################## NEWS 보여주기 Starts ##############################################

# Seeking Alpha 관련 뉴스 호출 함수
@app.post("/seekingNews", response_class=JSONResponse)
async def get_seekingNews(request: Request):
    form_data = await request.json()
    categories = form_data.get("categories", [])
    category_query = "|".join(categories)
    original_seekingNews = await rapidapi_seekingNews(category_query)
    seekingNews_data = extract_news_data(original_seekingNews)
    return JSONResponse(content=seekingNews_data)   
    
async def rapidapi_seekingNews(categories):
    url = "https://seeking-alpha.p.rapidapi.com/news/v2/list"
    querystring = {"category": categories, "size": "10", "number": "1"}
    #querystring  = {"category":"market-news::top-news|market-news::on-the-move|market-news::market-pulse|market-news::notable-calls|market-news::buybacks","size":"50","number":"1"}
    headers = {
	    "X-RapidAPI-Key": rapidAPI,
	    "X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com"
    }
    
    response = requests.get(url, headers=headers, params=querystring)
    return response.json()

'''# RapidAPI 테스트용
async def rapid():
    calendar_data = await rapidapi_calendar()
    print(calendar_data)
asyncio.run(rapid())'''

'''# Fred Data 테스트용
def fred_test():
    #data = fred.search_by_release(release_id=1, limit=0, order_by=None, filter="bonds")
    data2 = fred.get_data(api_name="series_search", search_text="FOMC")
    print(data2)
fred_test()'''

# 뉴스 json에서 gpt로 던질 내용만 뽑아내기
def extract_title_and_content(json_str):
    json_data = json.loads(json_str)
    title_and_content = []
    for item in json_data:
        title = item['title']
        content = item['content']
        title_and_content.append({'title': title, 'content': content})
    return title_and_content

# seeking alpha 뉴스에서 쓸데없는 파라미터들 없애기
def extract_news_data(news_json):
    extracted_data = []
    for item in news_json['data']:
        news_item = item['attributes']
        extracted_item = {
            'publishOn': news_item.get('publishOn', None),
            'gettyImageUrl': news_item.get('gettyImageUrl', None),
            'title': news_item.get('title', None),
            'content': news_item.get('content', None)
        }
        extracted_data.append(extracted_item)
    return json.dumps(extracted_data, indent=4, ensure_ascii=False)

# GPT4 에 뉴스요약을 요청 
async def gpt4_news_sum(newsData, SYSTEM_PROMPT):
    try:
        prompt = "다음이 system 이 이야기한 뉴스 데이터야. system prompt가 말한대로 실행해줘. 단 답변을 꼭 한국어로 해줘. 뉴스 데이터 : " + str(newsData)
        completion = client.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
                ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.error("An error occurred in gpt4_news_sum function: %s", str(e))
        return None

@app.post("/gptRequest")
async def gpt_request(request_data: dict):
    action = request_data.get("action")
    g_news = request_data.get("g_news")

    SYSTEM_PROMPT = ""
    if action == "translate":
        # 한국어로 번역하기에 대한 처리
        SYSTEM_PROMPT = "You are an expert in translation. Translate the title and content from the following JSON data into Korean. Return the translated content in the same JSON format, but only translate the title and content into Korean. Do not provide any other response besides the JSON format."
        gpt_result = await gpt4_news_sum(g_news, SYSTEM_PROMPT)

    elif action == "opinions":
        # AI 의견보기에 대한 처리
        SYSTEM_PROMPT = "Given the provided news data, please provide your expert analysis and insights on the current market trends and future prospects. Consider factors such as recent developments, market sentiment, and potential impacts on various industries based on the news. Your analysis should be comprehensive, well-informed, and forward-looking, offering valuable insights for investors and stakeholders. Thank you for your expertise"
        digest_news = extract_title_and_content(g_news)        
        gpt_result = await gpt4_news_sum(digest_news, SYSTEM_PROMPT)

    elif action == "summarize":
        # 내용 요약하기에 대한 처리
        SYSTEM_PROMPT = "You're an expert in data summarization. Given the provided JSON data, please summarize its contents systematically and comprehensively into about 20 sentences, ignoring JSON parameters unrelated to news articles."        
        digest_news = extract_title_and_content(g_news)
        gpt_result = await gpt4_news_sum(digest_news, SYSTEM_PROMPT)
        
    else:
        gpt_result = {"error": "Invalid action"}
    
    return {"result": gpt_result}

######################################## NEWS 보여주기 Ends  ##############################################

''' 테스트
async def gpttest():
    seekingNews_data = await rapidapi_seekingNews('market-news::top-news')
    digestNews = extract_title_and_content(seekingNews_data)
    print(digestNews)
    gpt_summary = await gpt4_news_sum(digestNews)   
    print("****************************************************************************")
    print(gpt_summary)
    
asyncio.run(gpttest()) '''
            
################################### FIN GPT 구현 부분 Starts (본부장님소스) ################################


def get_curday():
    return date.today().strftime("%Y-%m-%d")


def get_news (ticker, Start_date, End_date, count=20):
    news=finnhub_client.company_news(ticker, Start_date, End_date)
    if len(news) > count :
        news = random.sample(news, count)
    sum_news = ["[헤드라인]: {} \n [요약]: {} \n".format(
        n['headline'], n['summary']) for n in news]
    return sum_news 

def gen_term_stock (ticker, Start_date, End_date):
    df = yf.download(ticker, Start_date, End_date)['Close']
    term = '상승하였습니다' if df.iloc[-1] > df.iloc[0] else '하락하였습니다'
    terms = '{}부터 {}까지 {}의 주식가격은, $ {}에서 $ {}으로 {}. 관련된 뉴스는 다음과 같습니다.'.format(Start_date, End_date, ticker, int(df.iloc[0]), int(df.iloc[-1]), term)
    return terms 


# combine case1 and case2 
def get_prompt_earning (ticker):
    prompt_news_after7 = ''
    curday = get_curday()
    profile = finnhub_client.company_profile2(symbol=ticker)
    company_template = "[기업소개]:\n\n{name}은 {ipo}에 상장한 {finnhubIndustry}섹터의 기업입니다. "
    intro_company = company_template.format(**profile)    
    
    # find announce calendar 
    Start_date_calen = (datetime.strptime(curday, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d") # 현재 시점 - 3개월 
    End_date_calen = (datetime.strptime(curday, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")  # 현재 시점 + 1개월 
    announce_calendar= finnhub_client.earnings_calendar(_from=Start_date_calen, to=End_date_calen, symbol=ticker, international=False).get('earningsCalendar')[0]
        
    # get information from earning announcement
    date_announce= announce_calendar.get('date')
    eps_actual=announce_calendar.get('epsActual')
    eps_estimate=announce_calendar.get('epsEstimate')
    earning_y = announce_calendar.get('year')
    earning_q = announce_calendar.get('quarter')
    revenue_estimate=round(announce_calendar.get('revenueEstimate')/1000000)
       
    if eps_actual == None : # [Case2] 실적발표 전 
        # create Prompt 
        head = "{}의 {}년 {}분기 실적 발표일은 {}으로 예정되어 있습니다. 시장에서 예측하는 실적은 매출 ${}M, eps {}입니다. ".format(profile['name'], earning_y,earning_q, date_announce, revenue_estimate, eps_estimate)
        
        # [case2] 최근 3주간 데이터 수집  
        Start_date=(datetime.strptime(curday, "%Y-%m-%d") - timedelta(days=21)).strftime("%Y-%m-%d")
        End_date=curday
        
        # 뉴스 수집 및 추출 
        news = get_news (ticker, Start_date, End_date)
        terms_ = gen_term_stock(ticker, Start_date, End_date)
        prompt_news = "최근 3주간 {}: \n\n ".format(terms_)
        for i in news:
            prompt_news += "\n" + i 
        
        info = intro_company + '\n' + head 
        prompt = info + '\n' + prompt_news + '\n' + f"\n\n Based on all the information (from {Start_date} to {End_date}), let's first analyze the positive developments, potential concerns and stock price predictions for {ticker}. Come up with 5-7 most important factors respectively and keep them concise. Most factors should be inferred from company related news. " \
        f"Finally, make your prediction of the {ticker} stock price movement for next month. Provide a summary analysis to support your prediction."    
        SYSTEM_PROMPT = "You are a seasoned stock market analyst working in South Korea. Your task is to list the positive developments and potential concerns for companies based on relevant news and stock price of target companies, \
            Then, make analysis and prediction for the companies' stock price movement for the upcoming month. Your answer format should be as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n[Prediction & Analysis]:\n...\n\n  Because you are working in South Korea, all responses should be done in Korean not in English. \n "
    
    else : # [Case1] 실적발표 후
    
        # get additional information         
        excess_eps = round(abs(eps_actual / eps_estimate -1)* 100,1)
        revenue_actual=round(announce_calendar.get('revenueActual')/1000000)
        excess_revenue = round(abs(revenue_actual/revenue_estimate-1)*100,1)
        
        
        # create Prompt 
        term1 = '상회하였으며' if revenue_actual > revenue_estimate else '하회하였으며'
        term2 = '상회하였습니다.' if eps_actual > eps_estimate else '하회하였습니다'
        head = "\n [실적발표 요약]: \n {}에 {}년{}분기 {}의 실적이 발표되었습니다. 실적(매출)은 ${}M으로 당초 예측한 ${}M 대비 {}% {}, eps는 예측한 {}대비 {}으로 eps는 {}% {} ".format(date_announce,earning_y,earning_q, profile['name'], revenue_actual, revenue_estimate,excess_revenue,term1,eps_estimate, eps_actual, excess_eps, term2)
        
        
        # 기준점 산출 (세가지 시점)
        Start_date_before=(datetime.strptime(date_announce, "%Y-%m-%d") - timedelta(days=21)).strftime("%Y-%m-%d")
        End_date_before=(datetime.strptime(date_announce, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        Start_date_after = date_announce
        if datetime.strptime(curday, "%Y-%m-%d") < (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)):
            End_date_after = curday
        else :
            Start_date_after = date_announce
            End_date_after = (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
            Start_date_after7 = (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
            End_date_after7 = curday
        
        # 뉴스 수집 및 추출 (세가지 구간)
        news_before = get_news (ticker, Start_date_before, End_date_before)
        terms_before = gen_term_stock(ticker, Start_date_before, End_date_before)
        prompt_news_before = "Earning call 전, {}: \n\n ".format(terms_before)
        for i in news_before:
            prompt_news_before += "\n" + i 
        
        news_after = get_news (ticker, Start_date_after, End_date_after)
        terms_after = gen_term_stock(ticker, Start_date_after, End_date_after)
        prompt_news_after = "Earning call 후, {}: \n\n ".format(terms_after)
        for i in news_after:
            prompt_news_after += "\n" + i 

        
        if datetime.strptime(curday, "%Y-%m-%d") > (datetime.strptime(date_announce, "%Y-%m-%d") + timedelta(days=7)):
            news_after7 = get_news (ticker, Start_date_after7, End_date_after7)
            terms_after7 = gen_term_stock(ticker, Start_date_after7, End_date_after7)
            prompt_news_before = "Earning call 발표 7일 이후, {}: \n\n ".format(terms_after7)
            for i in news_after7:
                prompt_news_after7 += "\n" + i 
        else :
            prompt_news_after7 = 'Not enough time since the earnings announcement to monitor trends'
            
        
        info = intro_company + '\n' + head 
        prompt_news = prompt_news_before + '\n' + prompt_news_after + '\n' + prompt_news_after7  
        prompt = info + '\n' +  prompt_news + '\n' + f"\n\n Based on all the information before earning call (from {Start_date_before} to {End_date_before}), let's first analyze the positive developments, potential concerns and stock price predictions for {ticker}. Come up with 5-7 most important factors respectively and keep them concise. Most factors should be inferred from company related news. " \
        f"Then, based on all the information after earning call (from {date_announce} to {curday}), let's find 5-6 points that meet expectations and points that fall short of expectations when compared before the earning call. " \
        f"Finally, make your prediction of the {ticker} stock price movement for next month. Provide a summary analysis to support your prediction."    
        
        SYSTEM_PROMPT = "You are a seasoned stock market analyst working in South Korea. Your task is to list the positive developments and potential concerns for companies based on relevant news and stock price before an earning call of target companies, \
            then provide an market reaction with respect to the earning call. Finally, make analysis and prediction for the companies' stock price movement for the upcoming month. Your answer format should be as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n[Market Reaction After Earning Aall]:\n[Prediction & Analysis]:\n...\n\n  Because you are working in South Korea, all responses should be done in Korean not in English. \n "

    return info, prompt_news, prompt, SYSTEM_PROMPT

def query_gpt4(ticker: str):
    # get_prompt_earning 함수로부터 4개의 값을 올바르게 받음
    info, prompt_news, prompt, SYSTEM_PROMPT = get_prompt_earning(ticker)

    # OpenAI GPT-4 호출
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    completion_content = completion.choices[0].message.content if completion.choices else "No completion found."

    # FastAPI 클라로 보내기 위해 JSON으로 변환하여 반환
    return {
        "info": info,
        "prompt_news": prompt_news,
        "completion": completion_content
    }
    
def get_historical_eps(ticker, limit=4):
    earnings = finnhub_client.company_earnings(ticker, limit)
    earnings_json = [
        {
            "period":earning["period"],
            "actual":earning["actual"],
            "estimate":earning["estimate"],
            "surprisePercent":earning["surprisePercent"]
        } for earning in earnings 
    ]
    earnings_json.sort(key = lambda x:x['period'])
    df_earnings=pd.DataFrame(earnings_json)
    
    fig, ax = plt.subplots(figsize=(8,5))
    ax.scatter(df_earnings['period'], df_earnings['actual'],c='green', s=500, alpha=0.3, label='actual')
    ax.scatter(df_earnings['period'], df_earnings['estimate'],c='blue', s=500, alpha=0.3, label='estimate')
    ax.set_xlabel('announcement date', fontsize=15)
    ax.set_ylabel('eps', fontsize=15)
    ax.set_title('{} - Historical eps Surprise'.format(ticker), fontsize=17)
    ax.grid()
    ax.legend()

    for i in range(len(df_earnings)):
        plt.text(df_earnings['period'][i], df_earnings['actual'][i], ('Missed by ' if df_earnings['surprisePercent'][i] <0 else 'Beat by ')+ "{:.2f}".format(df_earnings['surprisePercent'][i])+"%",
                color='black' if df_earnings['surprisePercent'][i] <0 else 'red' , fontsize=11, ha='left', va='bottom')
    return fig
    
def get_recommend_trend (ticker) : 
    recommend_trend = finnhub_client.recommendation_trends(ticker)
    df_recommend_trend = pd.DataFrame(recommend_trend).set_index('period').drop('symbol', axis=1).sort_index()

    fig, ax = plt.subplots(figsize=(8,5))
    width = 0.6  
    
    bottom=np.zeros(len(df_recommend_trend))
    p1= ax.bar(df_recommend_trend.index,  df_recommend_trend['strongSell'], label='strong Sell', color='red', width=width, bottom=bottom)
    bottom +=df_recommend_trend['strongSell']
    p2= ax.bar(df_recommend_trend.index,  df_recommend_trend['sell'], label='Sell', color='orange',width=width,bottom=bottom)
    bottom +=df_recommend_trend['sell']
    p3= ax.bar(df_recommend_trend.index,  df_recommend_trend['hold'], label='Hold', color='grey',width=width,bottom=bottom)
    bottom +=df_recommend_trend['hold']
    p4= ax.bar(df_recommend_trend.index,  df_recommend_trend['buy'], label='Buy', color='skyblue',width=width,bottom=bottom)
    bottom +=df_recommend_trend['buy']
    p5= ax.bar(df_recommend_trend.index,  df_recommend_trend['strongBuy'], label='strong Buy', color='blue',width=width,bottom=bottom)
    
    if df_recommend_trend['strongSell'].sum() > 0 :
        ax.bar_label(p1, label_type='center')
    if df_recommend_trend['sell'].sum() > 0 :
        ax.bar_label(p2, label_type='center')
    if df_recommend_trend['hold'].sum() > 0 :
        ax.bar_label(p3, label_type='center')
    if df_recommend_trend['buy'].sum() > 0 :
        ax.bar_label(p4, label_type='center')
    if df_recommend_trend['strongBuy'].sum() > 0 :
        ax.bar_label(p5, label_type='center')
    
    plt.title('{} recommendation trend'.format(ticker), fontsize=12)
    plt.ylabel('Number of analysts')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1))
    return fig


def get_one_year_before(end_date):
  end_date = datetime.strptime(end_date, "%Y-%m-%d")
  one_year_before = end_date - timedelta(days=365)
  return one_year_before.strftime("%Y-%m-%d")

def get_stock_data_daily(symbol):
  EndDate = get_curday()
  StartDate = get_one_year_before(EndDate)
  stock_data = yf.download(symbol, StartDate, EndDate)
  return stock_data[["Adj Close", "Volume"]]

def get_stock_data_fig (ticker):
    data = get_stock_data_daily(ticker)
    fig, ax1 = plt.subplots(figsize=(14, 5))
    ax1.plot(data['Adj Close'], label='Price(USD)', color='blue')
    ax1.set_xlabel('date')
    ax1.set_ylabel('Price(USD)', color='blue')
    ax1.tick_params('y', colors='blue')
    ax1.set_title(f'{ticker} Stock price and Volume Chart (recent 1 year)')
    ax2 = ax1.twinx()
    ax2.bar(data.index, data['Volume'], label='Volume', alpha=0.2, color='green')
    ax2.set_ylabel('Volume', color='green')
    ax2.tick_params('y', colors='green')
    return fig 

# 차트를 Base64 인코딩된 문자열로 변환하는 함수
def get_chart_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)  # 차트 닫기
    return base64.b64encode(buf.getvalue()).decode('utf-8')

@app.get("/api/charts/both/{ticker}")
async def get_both_charts(ticker: str):
    # 주식 실적 이력 차트 생성 및 Base64 인코딩
    fig1 = get_historical_eps(ticker)
    earnings_chart_base64 = get_chart_base64(fig1)
    
    #print(earnings_chart_base64)
    # 애널리스트 추천 트렌드 차트 생성 및 Base64 인코딩
    fig2 = get_recommend_trend(ticker)
    recommendations_chart_base64 = get_chart_base64(fig2)

    # 두 차트의 Base64 인코딩된 이미지 데이터를 JSON으로 반환
    return JSONResponse(content={
        "earnings_chart": earnings_chart_base64,
        "recommendations_chart": recommendations_chart_base64
    })
  
@app.get("/api/analysis/{ticker}")
def get_analysis(ticker: str):
    result = query_gpt4(ticker)
    return JSONResponse(content=result)
 
@app.get("/api/stockwave/{ticker}")
def get_stockwave(ticker: str):
    fig = get_stock_data_fig(ticker)
    logging.debug(fig)
    stockwave_base64 = get_chart_base64(fig)
    return JSONResponse(content={"stockwave_data": stockwave_base64})

#################################### FIN GPT 구현 부분 Ends (본부장님소스) ###################################

''' 테스트
async def cccc():
    earnings_chart = await get_both_charts('AAPL')
    print(earnings_chart)
asyncio.run(cccc())'''

'''def queryGPT4():
    result = query_gpt4('AAPL')
    print(result)
queryGPT4()'''