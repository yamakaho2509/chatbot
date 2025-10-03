import streamlit as st
import requests
import json
import time

# Create a session state variable for "chat_started"
if "chat_started" not in st.session_state:
    st.session_state.chat_started = False

# Show title and description.
st.title("💬 学習目標設定チャットボット")
st.write(
    "このチャットボットは、あなたの学習目標達成をサポートします。目標を具体的に設定して、学習の進捗を管理しましょう！"
)

# --- Check if the conversation has started ---
if not st.session_state.chat_started:
    # --- Add input fields for user goals on the landing page ---
    st.header("あなたの学習目標を設定しましょう")
    learning_theme = st.text_input("① どんなテーマの学習に取り組んでいますか？ (例：簿記、英語、資格試験、業務スキルなど)", key="theme_input")
    goal_date_and_progress = st.text_input("② いつまでにどのくらいの進捗を目指していますか？ (例：1か月後にテキスト1冊終える、来月の試験に合格する など)", key="date_input")
    achievement_criteria = st.text_input("③ 「達成できた！」と感じるために、どんな行動や成果物があればよいですか？ (例：練習問題を9割正答、英単語を毎日30語覚える)", key="criteria_input")

    # Add a button to submit the goals
    if st.button("目標を送信", key="submit_button"):
        # Create a single message with all three user inputs
        user_prompt = f"私の学習目標です。この情報に基づいて、考えを深めるための質問を1つだけ返してください。\n\n① テーマ: {learning_theme}\n② 進捗: {goal_date_and_progress}\n③ 達成基準: {achievement_criteria}"

        # Use st.secrets to access the API key stored in .streamlit/secrets.toml
        google_api_key = st.secrets.get("GOOGLE_API_KEY")

        if not google_api_key:
            st.error("secrets.tomlファイルにGoogle APIキーが設定されていません。")
        else:
            # Set up the Gemini API endpoint
            API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={google_api_key}"

            # Set the detailed system prompt for the chatbot's role
            system_prompt = """
            あなたは優秀なインストラクショナル・デザイナーであり、孤独の中独学をする成人学習者の自己成長を支援するコーチとしての役割を担う親しみやすいチャットボットです。学習支援に際して、まず学習目標を設定できるよう、対話を通して支援してください。
            
            目標設定のポイント：
            * 学習目標は、行動目標で示してください。
            * 学習目標は、達成できたか評価できるようにしてください。
            * 学習目標と合わせて、合格基準を設定してください。
            
            その他目標設定にいけるインストラクション：
            * 上記の条件を満たす目標を設定するために、学習者に「どのようなテーマや目標に取り組みたいか」を積極的に尋ねて対話してください。
            * 学習者は、教材をすでに持っていて、いつまでに何を達成するかを定められている場合が多く想定されるので、あるものを活用した学習の伴奏を行う立ち位置から支援してください。
            * 学習者が話しやすい雰囲気で質問し、学習テーマや目標の具体化を支援してください。
            * 必要な情報が集まったら、学習目標を定め学習者に提案してください。イメージと異なる場合、追加で質問をして形を整えてください。
            * 学習者はすでに学習したい内容の教材やスケジュールは組んでいることを仮定します。スケジュール作成や学習内容の選定の支援は必要ありません。
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

            # Create a session state variable to store the chat messages.
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Store and display the user's combined prompt
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            # Prepare the chat history for the Gemini API.
            history = []
            for msg in st.session_state.messages:
                role = "user" if msg["role"] == "user" else "model"
                history.append({"role": role, "parts": [{"text": msg["content"]}]})
            
            # Include the system prompt in the API payload
            payload = {
                "contents": history,
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                }
            }

            # Implement exponential backoff for API requests
            retries = 3
            delay = 1

            for i in range(retries):
                try:
                    # Send the request to the Gemini API.
                    response = requests.post(API_URL, json=payload)
                    response.raise_for_status()

                    # Parse the JSON response.
                    response_json = response.json()
                    gemini_response = response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'エラー: 応答がありませんでした。')

                    # Display the Gemini response.
                    with st.chat_message("assistant"):
                        st.markdown(gemini_response)

                    # Store the Gemini response in session state.
                    st.session_state.messages.append({"role": "assistant", "content": gemini_response})
                    
                    # Set chat_started to True to trigger the chat UI
                    st.session_state.chat_started = True
                    st.rerun()
                    
                    # If successful, break the loop
                    break

                except requests.exceptions.RequestException as e:
                    st.error(f"APIリクエスト中にエラーが発生しました: {e}")
                    if i < retries - 1:
                        st.info(f"リトライします... {delay}秒後")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        st.error("リトライの最大回数に達しました。")
                except (IndexError, KeyError) as e:
                    st.error(f"API応答の解析中にエラーが発生しました: {e}")
                    break
else:
    # --- Display chat messages and add chat input after the initial goal submission ---
    # Display existing messages if any
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Check for keywords to end the conversation
    if "finalized_goal" not in st.session_state:
        st.session_state.finalized_goal = False

    # Only show the chat input box if a conversation has started and not finalized
    if not st.session_state.finalized_goal:
        if prompt := st.chat_input("何が知りたいですか？"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Check if the user's prompt contains a finalization keyword
            finalization_keywords = ["これでいい", "これでOK", "これで決定", "目標確定", "はい"]
            is_finalizing = any(keyword in prompt for keyword in finalization_keywords)

            history = []
            for msg in st.session_state.messages:
                role = "user" if msg["role"] == "user" else "model"
                history.append({"role": role, "parts": [{"text": msg["content"]}]})

            # System prompt for ongoing conversation
            system_prompt_ongoing = """
            あなたは優秀なインストラクショナル・デザイナーであり、孤独の中独学をする成人学習者の自己成長を支援するコーチとしての役割を担う親しみやすいチャットボットです。学習支援に際して、まず学習目標を設定できるよう、対話を通して支援してください。
            
            目標設定のポイント：
            * 学習目標は、行動目標で示してください。
            * 学習目標は、達成できたか評価できるようにしてください。
            * 学習目標と合わせて、合格基準を設定してください。
            
            その他目標設定にいけるインストラクション：
            * 上記の条件を満たす目標を設定するために、学習者に「どのようなテーマや目標に取り組みたいか」を積極的に尋ねて対話してください。
            * 学習者は、教材をすでに持っていて、いつまでに何を達成するかを定められている場合が多く想定されるので、あるものを活用した学習の伴奏を行う立ち位置から支援してください。
            * 学習者が話しやすい雰囲気で質問し、学習テーマや目標の具体化を支援してください。
            * 必要な情報が集まったら、学習目標を定め学習者に提案してください。イメージと異なる場合、追加で質問をして形を整えてください。
            * 学習者はすでに学習したい内容の教材やスケジュールは組んでいることを仮定します。スケジュール作成や学習内容の選定の支援は必要ありません。
            * 返答には、必ず質問を1つだけ含めてください。追加で質問したいことがある場合でも、1つの返答に複数の質問を入れないでください。
            * ユーザーが「これでいい」「OK」「目標確定」などのキーワードを使って目標に同意したら、対話を終了し、最終目標をまとめてください。
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

            # Payload for API request
            payload = {
                "contents": history,
                "systemInstruction": {
                    "parts": [{"text": system_prompt_ongoing}]
                }
            }
            google_api_key = st.secrets.get("GOOGLE_API_KEY")
            API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={google_api_key}"

            retries = 3
            delay = 1

            for i in range(retries):
                try:
                    response = requests.post(API_URL, json=payload)
                    response.raise_for_status()
                    response_json = response.json()
                    gemini_response = response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'エラー: 応答がありませんでした。')
                    
                    with st.chat_message("assistant"):
                        st.markdown(gemini_response)
                    st.session_state.messages.append({"role": "assistant", "content": gemini_response})

                    if "最終目標" in gemini_response:
                        st.session_state.finalized_goal = True
                        st.info("目標設定が完了しました。")
                    
                    break
                except requests.exceptions.RequestException as e:
                    st.error(f"APIリクエスト中にエラーが発生しました: {e}")
                    if i < retries - 1:
                        st.info(f"リトライします... {delay}秒後")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        st.error("リトライの最大回数に達しました。")
                except (IndexError, KeyError) as e:
                    st.error(f"API応答の解析中にエラーが発生しました: {e}")
                    break
    else:
        st.info("目標設定は完了しました。新しい目標を設定するには、ページを再読み込みしてください。")
