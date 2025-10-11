import streamlit as st
import requests
import time
import json

# --- 1. アプリの初期設定と関数定義 ---

# セッションステートの初期化
if "chat_started" not in st.session_state:
    st.session_state.chat_started = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "finalized_goal" not in st.session_state:
    st.session_state.finalized_goal = False

def get_google_api_key():
    """StreamlitのsecretsからGoogle APIキーを取得する"""
    google_api_key = st.secrets.get("GOOGLE_API_KEY")
    if not google_api_key:
        st.error("secrets.tomlファイルにGoogle APIキーが設定されていません。")
        return None
    return google_api_key

def call_gemini_api(history, system_prompt):
    """Gemini APIを呼び出し、応答を返す関数"""
    google_api_key = get_google_api_key()
    if not google_api_key:
        return 'エラー: APIキーが見つかりません。'

    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={google_api_key}"
    
    payload = {
        "contents": history,
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        }
    }

    retries = 3
    delay = 1
    for i in range(retries):
        try:
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            response_json = response.json()
            return response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'エラー: 応答がありませんでした。')
        except requests.exceptions.RequestException as e:
            st.error(f"APIリクエスト中にエラーが発生しました: {e}")
            if i < retries - 1:
                st.info(f"リトライします... {delay}秒後")
                time.sleep(delay)
                delay *= 2
            else:
                st.error("リトライの最大回数に達しました。")
                return 'エラー: APIリクエストに失敗しました。'
        except (IndexError, KeyError) as e:
            st.error(f"API応答の解析中にエラーが発生しました: {e}")
            return 'エラー: API応答の解析に失敗しました。'
    return 'エラー: 応答を取得できませんでした。'

# --- 2. システムプロンプト定義 ---

SYSTEM_PROMPT_INITIAL = """
あなたは優秀なインストラクショナル・デザイナーであり、孤独の中独学をする成人学習者の自己成長を支援するコーチとしての役割を担う親しみやすいチャットボットです。学習支援に際して、まず学習目標を設定できるよう、対話を通して支援してください。
            
目標設定のポイント：
* 学習目標は、行動目標で示してください。
* 学習目標は、達成できたか評価できるようにしてください。
* 学習目標と合わせて、合格基準を設定してください。
            
その他目標設定にいけるインストラクション：
* 上記の条件を満たす目標を設定するために、学習者に「どのようなテーマや目標に取り組みたいか」を積極的に尋ねて対話してください。
* 学習者は、教材をすでに持っていて、いつまでに何を達成するかを定められている場合が多く想定されるので、あるものを活用した学習の伴奏を行う立ち位置から支援してください。
* 学習者はすでに学習したい内容の教材やスケジュールは組んでいることを仮定します。スケジュール作成や学習内容の選定の支援は必要ありません。
* 学習者が話しやすい雰囲気で質問し、学習テーマや目標の具体化を支援してください。
* 必要な情報が集まったら、必ず学習目標案の候補を3つ学習者に提案して学習者に学習目標を選ばせるようにしてください。
* 3つの案の中で納得できるものがあれば、それを返信として入力してもらうよう指示してください。どれもイメージと異なる場合、「イメージと異なる」と返答するよう指示してください。
* 「イメージと異なる」と学習者が返答した場合。追加で質問をして情報を集め、再度学習目標案の候補を3つ学習者に提案するところから行ってください。
* 返答には、必ず質問を1つだけ含めてください。追加で質問したいことがある場合でも、1つの返答に複数の質問を入れないでください。
* 対話がまとまり、ユーザーが目標に納得したら、最終的な目標を明確に要約し、以下の形式で提示してください。
            
---
## あなたの学習目標が固まりましたね！👏
            
**テーマ**: (これまでの対話から抽出)
**目標期限**: (これまでの対話から抽出)
**達成基準**: (これまでの対話から抽出)
            
**最終目標**: 
(これまでの対話内容をSMARTゴールに基づいて1つの具体的な行動目標としてまとめる)
            
---
            
これで目標設定は完了です。この目標に向かって、頑張ってくださいね！応援しています！🎉
            
上記の形式を提示した後は、対話を終了してください。
"""

SYSTEM_PROMPT_ONGOING = """
あなたは優秀なインストラクショナル・デザイナーであり、孤独の中独学をする成人学習者の自己成長を支援するコーチとしての役割を担う親しみやすいチャットボットです。学習支援に際して、まず学習目標を設定できるよう、対話を通して支援してください。
            
目標設定のポイント：
* 学習目標は、行動目標で示してください。
* 学習目標は、達成できたか評価できるようにしてください。
* 学習目標と合わせて、合格基準を設定してください。
            
その他目標設定にいけるインストラクション：
* 上記の条件を満たす目標を設定するために、学習者に「どのようなテーマや目標に取り組みたいか」を積極的に尋ねて対話してください。
* 学習者は、教材をすでに持っていて、いつまでに何を達成するかを定められている場合が多く想定されるので、あるものを活用した学習の伴奏を行う立ち位置から支援してください。
* 学習者が話しやすい雰囲気で質問し、学習テーマや目標の具体化を支援してください。
* 必要な情報が集まったら、必ず学習目標案の候補を3つ学習者に提案して学習者に学習目標を選ばせるようにしてください。
* 3つの案の中で納得できるものがあれば、それを返信として入力してもらうよう指示してください。どれもイメージと異なる場合、「イメージと異なる」と返答するよう指示してください。
* 「イメージと異なる」と学習者が返答した場合。追加で質問をして情報を集め、再度学習目標案の候補を3つ学習者に提案するところから行ってください。
* 返答には、必ず質問を1つだけ含めてください。追加で質問したいことがある場合でも、1つの返答に複数の質問を入れないでください。
* ユーザーが目標に同意したと判断した場合、対話を終了し、最終目標をまとめてください。
* 最終目標のまとめ方は、以下の形式に従い、これまでの対話内容を反映してください。
            
---
## あなたの学習目標が固まりましたね！👏
            
**テーマ**: (これまでの対話から抽出)
**目標期限**: (これまでの対話から抽出)
**達成基準**: (これまでの対話から抽出)
            
**最終目標**: 
(これまでの対話内容をSMARTゴールに基づいて1つの具体的な行動目標としてまとめる)
            
---
            
これで目標設定は完了です。この目標に向かって、頑張ってくださいね！応援しています！🎉
            
上記の形式を提示した後は、対話を終了してください。
"""

# --- 3. UIとロジックの描画 ---

st.title("💬 学習目標設定チャットボット")
st.write(
    "このチャットボットは、あなたの学習目標達成をサポートします。具体的な目標を明文化しましょう！"
)

# チャット開始前の目標入力画面
if not st.session_state.chat_started:
    st.header("あなたの学習目標を設定しましょう")
    learning_theme = st.text_input("① どんなテーマの学習に取り組んでいますか？ (例：簿記、英語、資格試験、業務スキルなど)", key="theme_input")
    goal_date_and_progress = st.text_input("② いつまでにどのくらいの進捗を目指していますか？ (例：1か月後にテキスト1冊終える、来月の試験に合格する など)", key="date_input")
    achievement_criteria = st.text_input("③ 「達成できた！」と感じるために、どんな行動や成果物があればよいですか？ (例：練習問題を9割正答、英単語を毎日30語覚える)", key="criteria_input")

    if st.button("目標を送信", key="submit_button"):
        user_prompt = f"私の学習目標です。この情報に基づいて、考えを深めるための質問を1つだけ返してください。\n\n① テーマ: {learning_theme}\n② 進捗: {goal_date_and_progress}\n③ 達成基準: {achievement_criteria}"
        
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        history = [{"role": "user", "parts": [{"text": user_prompt}]}]
        gemini_response = call_gemini_api(history, SYSTEM_PROMPT_INITIAL)

        with st.chat_message("assistant"):
            st.markdown(gemini_response)
        st.session_state.messages.append({"role": "assistant", "content": gemini_response})
        
        st.session_state.chat_started = True
        st.rerun()

# チャット開始後の画面
else:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not st.session_state.finalized_goal:
        if prompt := st.chat_input("何が知りたいですか？"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # ユーザーの入力に基づいて使用するプロンプトを切り替える
            finalization_keywords = ["これでいい", "これでOK", "これで決定", "目標確定", "はい"]
            is_finalizing = any(keyword in prompt for keyword in finalization_keywords)

            history
