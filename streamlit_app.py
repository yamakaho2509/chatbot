import streamlit as st
import requests
import json
import time
import os

# --- Configuration & Constants ---

# システムプロンプトを定数として定義し、一元管理します。
SYSTEM_PROMPT = """
あなたは優秀なインストラクショナル・デザイナーであり、孤独の中独学をする成人学習者の自己成長を支援するコーチとしての役割を担う親しみやすいチャットボットです。
学習支援に際して、まず学習目標を設定できるよう、対話を通して支援してください。

目標設定のポイント：
* 学習目標は、**行動目標**で示してください。
* 学習目標は、**達成できたか評価できるように**してください。
* 学習目標と合わせて、合格基準を設定してください。

その他目標設定におけるインストラクション：
* 上記の条件を満たす目標を設定するために、学習者に「どのようなテーマや目標に取り組みたいか」を積極的に尋ねて対話してください。
* 学習者は、教材をすでに持っていて、いつまでに何を達成するかを定められている場合が多く想定されるので、あるものを活用した学習の伴奏を行う立ち位置から支援してください。
* 学習者はすでに学習したい内容の教材やスケジュールは組んでいることを仮定します。スケジュール作成や学習内容の選定の支援は必要ありません。
* 学習者が話しやすい雰囲気で質問し、学習テーマや目標の具体化を支援してください。
* **返答には、必ず質問を1つだけ含めてください**。追加で質問したいことがある場合でも、1つの返答に複数の質問を入れないでください。

* **目標候補の提示フェーズのルール（重要）**:
  * 必要な情報が集まったら、**最終目標のまとめ形式（---で始まるブロック）を絶対に使わず**、学習目標案の候補を3つ学習者に提案し、選択肢（1, 2, 3または「イメージと異なる」）から選ぶよう指示してください。
  * 「イメージと異なる」という返答があった場合は、追加で質問をして情報を集め、再度3案を提示してください。

* **最終目標の確定フェーズのルール（重要）**:
  * ユーザーが3つの案の中から1つを選んだ、または「これでいい」「OK」「目標確定」などのキーワードで目標に同意したと判断した場合に限り、対話を終了し、最終的な目標を明確に要約し、**必ず以下の形式**で提示してください。

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

# --- Helper Functions ---

def get_gemini_response_with_retry(history: list, system_prompt: str):
    """
    Gemini APIを呼び出し、指数バックオフでリトライ処理を行うヘルパー関数。
    成功したレスポンスのテキストを返す。失敗した場合はエラーメッセージを表示する。
    """
    # StreamlitのsecretsからAPIキーを取得
    google_api_key = st.secrets.get("GOOGLE_API_KEY")

    if not google_api_key:
        st.error("secrets.tomlファイルにGoogle APIキーが設定されていません。")
        return None

    # ユーザーが指定したモデルを使用 (必要に応じて変更してください)
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={google_api_key}"
    
    payload = {
        "contents": history,
        # systemInstructionをAPIペイロードのトップレベルに配置
        "config": {
            "systemInstruction": system_prompt
        }
    }

    retries = 3
    delay = 1

    for i in range(retries):
        try:
            # APIリクエストを送信
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()

            # JSON応答を解析
            response_json = response.json()
            
            # 応答テキストを抽出
            gemini_response = response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'エラー: 応答がありませんでした。')
            
            # API応答でシステムプロンプトの指定形式が正しく反映されない場合があるため、
            # contentではなくpartsから直接textを取得するロジックを修正し、安定化
            if gemini_response:
                return gemini_response
            
            # 応答が空または予期しない形式だった場合
            raise ValueError("APIから有効なテキスト応答が得られませんでした。")

        except requests.exceptions.RequestException as e:
            st.error(f"APIリクエスト中にエラーが発生しました: {e}")
            if i < retries - 1:
                st.info(f"リトライします... {delay}秒後")
                time.sleep(delay)
                delay *= 2
            else:
                st.error("リトライの最大回数に達しました。")
                break
        except (IndexError, KeyError, ValueError) as e:
            st.error(f"API応答の解析中にエラーが発生しました: {e}")
            break
            
    return None

# --- Streamlit App Logic ---

# Session State変数の初期化
if "chat_started" not in st.session_state:
    st.session_state.chat_started = False
if "messages" not in st.session_state:
    # メッセージ履歴はAPIのcontents形式に合わせて初期化
    st.session_state.messages = [] 
if "finalized_goal" not in st.session_state:
    st.session_state.finalized_goal = False

# タイトルと説明の表示
st.title("💬 学習目標設定チャットボット")
st.write(
    "このチャットボットは、あなたの学習目標達成をサポートします。具体的な目標を明文化しましょう！"
)

def handle_initial_goal_setting():
    """初期の目標設定フォームを処理する"""
    st.header("あなたの学習目標を設定しましょう")
    
    # st.empty()を使って、フォーム送信後にフォームを非表示にする
    form_placeholder = st.empty()

    with form_placeholder.container():
        learning_theme = st.text_input("① どんなテーマの学習に取り組んでいますか？ (例：簿記、英語、資格試験、業務スキルなど)", key="theme_input")
        goal_date_and_progress = st.text_input("② いつまでにどのくらいの進捗を目指していますか？ (例：1か月後にテキスト1冊終える、来月の試験に合格する など)", key="date_input")
        achievement_criteria = st.text_input("③ 「達成できた！」と感じるために、どんな行動や成果物があればよいですか？ (例：練習問題を9割正答、英単語を毎日30語覚える)", key="criteria_input")

        if st.button("目標を送信", key="submit_button"):
            # すべてのフィールドが入力されているかチェック
            if not learning_theme or not goal_date_and_progress or not achievement_criteria:
                st.warning("すべてのフィールドを入力してください。")
                return

            # ユーザー入力を統合したプロンプトを作成
            user_prompt = (
                f"私の学習目標です。この情報に基づいて、考えを深めるための質問を1つだけ返してください。\n\n"
                f"① テーマ: {learning_theme}\n"
                f"② 進捗: {goal_date_and_progress}\n"
                f"③ 達成基準: {achievement_criteria}"
            )

            # フォームを非表示にする (st.empty()を使用)
            form_placeholder.empty()

            # ユーザープロンプトを履歴に追加
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            
            with st.chat_message("user"):
                st.markdown(user_prompt)

            # API呼び出し用に履歴を整形
            # Gemini APIは、rolesが "user" と "model" であり、partsがテキストを含む形式を要求します。
            history = [
                {"role": msg["role"], "parts": [{"text": msg["content"]}]} 
                for msg in st.session_state.messages
            ]
            
            # ヘルパー関数でAPIを呼び出す
            with st.spinner("目標設定アシスタントが応答を生成中です..."): # ローディングスピナーを追加
                gemini_response = get_gemini_response_with_retry(history, SYSTEM_PROMPT)

            if gemini_response:
                # Geminiの応答を表示
                with st.chat_message("assistant"):
                    st.markdown(gemini_response)

                # Geminiの応答を履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": gemini_response})
                
                # API呼び出しと履歴への追加が成功した場合にのみチャット開始フラグを立てて再実行
                st.session_state.chat_started = True
                st.rerun()
            else:
                # API呼び出しが失敗した場合は、エラーメッセージを表示したままフォームを再表示（またはエラー状態を維持）
                # ただし、form_placeholder.empty()でフォームは消えているため、エラーメッセージを明示的に残す
                st.error("APIからの応答が得られませんでした。Google APIキーとネットワーク接続を確認してください。")


def handle_ongoing_chat():
    """目標送信後の継続的なチャット対話を処理する"""
    # 既存のメッセージを表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 最終目標が確定していない場合のみチャット入力ボックスを表示
    if not st.session_state.finalized_goal:
        if prompt := st.chat_input("質問に回答するか、さらに目標を具体化するための情報を入力してください。"):
            # ユーザーの新しいプロンプトを履歴に追加して表示
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # API呼び出し用に履歴を整形
            history = [
                {"role": msg["role"], "parts": [{"text": msg["content"]}]} 
                for msg in st.session_state.messages
            ]

            # ヘルパー関数でAPIを呼び出す
            with st.spinner("アシスタントが応答を考えています..."):
                gemini_response = get_gemini_response_with_retry(history, SYSTEM_PROMPT)

            if gemini_response:
                # Geminiの応答を表示
                with st.chat_message("assistant"):
                    st.markdown(gemini_response)
                
                # Geminiの応答を履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": gemini_response})

                # 最終目標の形式が出力されたかチェックし、チャットを終了
                # LLMが指定された形式を使用しているかを確認
                if "## あなたの学習目標が固まりましたね！" in gemini_response:
                    st.session_state.finalized_goal = True
                    st.rerun() # 状態が変更されたら再実行してダウンロードボタンを表示
            
            # API呼び出し後にチャット入力が自動的にクリアされないため、手動で再実行
            st.rerun() 
    else:
        # 目標確定後のメッセージとダウンロードボタンを表示
        st.info("目標設定は完了しました。お疲れ様でした！この目標に向かって、頑張ってくださいね！")
        
        # --- ダウンロードボタンのロジック (ファイル名「nikki.docx」を反映) ---
        st.markdown("---")
        st.header("学習計画テンプレートのダウンロード")
        st.write("このテンプレートを活用して、今後の学習をさらに具体的に計画してみましょう。")
        
        # テンプレートファイルのパスを新しいファイル名に設定 (nikki.docxに変更)
        template_file_path = "templates/nikki.docx"
        
        # ファイルが存在するか確認 (ローカル環境での実行を想定)
        if os.path.exists(template_file_path):
            try:
                # バイナリモードでファイルを読み込む (Wordファイルはバイナリです)
                with open(template_file_path, "rb") as f:
                    template_data = f.read()
                
                st.download_button(
                    label="📥 日記テンプレをダウンロード",
                    data=template_data,
                    # ダウンロード時のファイル名も新しい名前に設定
                    file_name="nikki.docx", 
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
        else:
            st.warning(f"注意: テンプレートファイル '{template_file_path}' が見つかりません。ダウンロードボタンを表示するには、このファイルをプロジェクトの 'templates' フォルダに配置してください。")

# --- Main App Execution ---

# チャット開始前は初期設定フォームを表示し、開始後は継続的なチャットを処理
if not st.session_state.chat_started:
    handle_initial_goal_setting()
else:
    handle_ongoing_chat()
