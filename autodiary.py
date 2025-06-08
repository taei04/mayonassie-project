# autodiary.py

import os
from flask import Blueprint, request, jsonify, render_template, session
from datetime import datetime
from gpt_utils import analyze_emotions_with_gpt, extract_emotion_scores
import sqlite3
import openai

# Blueprint 객체 생성
autodiary_bp = Blueprint('autodiary', __name__, template_folder='templates')

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

@autodiary_bp.route("/api/has_survey", methods=["GET"])
def has_survey():
    # TODO: 실제 DB에서 설문 완료 여부를 확인하도록 구현하세요.
    # 현재는 항상 True를 반환하도록 설정했습니다.
    return jsonify({"hasSurvey": True})

@autodiary_bp.route("/generate_autodiary", methods=["POST"])
def generate_autodiary():
    data = request.get_json()
    answers = data.get("answers", [])
    user_id = session.get("userid", None)

    # 최근 설문 데이터 가져오기
    conn = sqlite3.connect("emotion.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM survey_results WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()
    col_names = [desc[0] for desc in cursor.description]
    conn.close()

    # 🎯 리팩토링된 감정 점수 계산
    scores = extract_emotion_scores(row, col_names)
    score_text = "\n".join([f"{k}: {v}" for k, v in scores.items()])

    # 프롬프트 구성
    diary_prompt = "다음은 사용자의 최근 감정 상태입니다. 이것을 참고하여 일기의 분위기를 자연스럽게 반영해 주세요.\n"
    diary_prompt += score_text + "\n\n"
    diary_prompt += "다음은 오늘 사용자가 대답한 질문과 답변입니다:\n\n"
    for qa in answers:
        q = qa.get("question", "(질문 없음)")
        a = qa.get("answer", "(답변 없음)")
        diary_prompt += f"Q: {q}\nA: {a}\n\n"

    try:
        # GPT 호출
        resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """
    너는 오늘 내가 스스로 떠올린 말들로 일기를 쓰는 사람이다.
    아래 여섯 가지 질문을 떠올리며, 오늘 내게 일어난 일과 그 순간 느낀 감정·앎·여운·다짐을 자연스럽게 풀어내야 한다.

    ## 작성 가이드
    - 첫 줄에 “[오늘의 일기]”만 쓰고, 다음 줄부터는 모두 “나” 시점으로 간단하게 적는다.
    - 한 문장 안에서 “시간·장소·상황”을 연속으로 적지 말고, 예: “오후에 운동장 한켠에 서 있었다.”처럼 각 요소가 맥락 속에 녹아들게 한다.
    - 지나치게 짤막하게 끊지 말고, 최대한 **두세 문장**을 연결해 장면과 감정이 자연스럽게 흐르도록 작성한다.
    - 모든 문장은 "‘~다’ 종결어미”로 끝나되, 중간에 쉼표나 연결어(“그러나”, “그래서”, “그리고”)를 사용해 부드럽게 이어준다.
    - **감성적인 묘사**를 살짝 녹인다. 예: “가슴속에 작은 파도가 일렁이는 듯했다” “침묵이 잔잔하게 깔렸다”처럼 비유나 이미지를 곁들인다.
    - 일기 전체는 2~3문단, 총 5~7문장 정도로 구성하되, **“상황 → 감정 → 깨달음 및 다짐”** 흐름이 자연스럽게 이어지도록 한다.
    - 감정 점수나 설문 질문을 **직접 인용하지 말고**, 내가 실제로 느낀 듯한 말투로 녹여서 쓴다.
    - 너무 직접적인 해결책 대신, “오늘 내가 이러이러했구나” 하는 **내면의 성찰**을 중심으로 적는다.

                 종결어미는 '~다'로 끝내
                 사용자가 낸 오타는 수정해서 일기에 적용시켜
    이제 위 가이드와 질문을 참고해서, 오늘 내가 느낀 감정과 답변을 바탕으로 **정말 내가 쓴 것처럼** 자연스럽고 감성적인 일기를 작성해라.

"""},
                {"role": "user", "content": diary_prompt}
            ],
            temperature=0.8,
            max_tokens=500
        )
        diary = resp.choices[0].message.content.strip()
        return jsonify({"diary": diary})
    except Exception as e:
        import traceback
        print("❌ GPT 호출 오류:", str(e))
        traceback.print_exc()
        return jsonify({"error": "GPT 호출 실패"}), 500


@autodiary_bp.route("/autodiary_complete", methods=["POST"])
def autodiary_complete():
    from flask import session
    if "userid" not in session:
        return "로그인 필요", 401

    data = request.get_json()
    content = data.get("content", "")
    user_id = session["userid"]

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    conn = sqlite3.connect("emotion.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO diary (user_id, date, time, content)
        VALUES (?, ?, ?, ?)
    """, (user_id, date, time, content))
    conn.commit()
    conn.close()

    return jsonify({"message": "자동일기 저장 완료!"})


@autodiary_bp.route('/autodiary')
def autodiary_page():
    # templates/autodiary.html 을 렌더링해 서빙
    return render_template('autodiary.html')