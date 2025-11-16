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
  * 必要な情報が集まったら、**最終目標のまとめ形式（---で始まるブロック）を絶対に使わず**、学習目標案の候補を3つ学習者に提案し、選択肢（1, 2, 3または「イメージと異なる」）から選ぶよう指示してください。**その際、各候補は「1. 」「2. 」「3. 」のように数字から始まるプレーンなテキストで記述し、見出し記法(#)は絶対に使用しないでください。**
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
    # ローカル実行環境に合わせたsecretsの取得
    google_api_key = os.environ.get("GOOGLE_API_KEY") 
    if not google_api_key:
         google_api_key = st.secrets.get("GOOGLE_API_KEY")

    if not google_api_key:
        st.error("Google APIキーが設定されていません。環境変数またはsecrets.tomlファイルを確認してください。")
        return None

    # 404エラーを修正したURL
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
            # APIリクエストを送信
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()

            # JSON応答を解析
            response_json = response.json()
            gemini_response = response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'エラー: 応答がありませんでした。')
            return gemini_response

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
            
    return None

# --- Streamlit App Logic ---

# Create session state variables if they don't exist
if "chat_started" not in st.session_state:
    st.session_state.chat_started = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "finalized_goal" not in st.session_state:
    st.session_state.finalized_goal = False

# Show title and description.
st.title("💬 学習目標設定チャットボット")
st.write(
    "このチャットボットは、あなたの学習目標達成をサポートします。具体的な目標を明文化しましょう！"
)

def handle_initial_goal_setting():
    """初期の目標設定フォームを処理する"""
    st.header("あなたの学習目標を設定しましょう")
    
    # CSSを注入して余白を調整
    # st.markdown(質問文)とst.caption(例)の間、st.caption(例)とst.text_input(入力欄)の間を詰める
    # Streamlitのバージョンによるセレクタの違いを考慮し、複数の可能性を試す
    st.markdown("""
    <style>
        /* st.markdown(質問文) の下の余白を詰める (最新のStreamlitはstMarkdownContainer) */
        div[data-testid="stMarkdownContainer"] p {
            margin-bottom: 2px; /* 質問文と例の間の余白 */
        }
        /* 古いStreamlit (stMarkdown) */
        div[data-testid="stMarkdown"] p {
            margin-bottom: 2px; /* 質問文と例の間の余白 */
        }

        /* st.caption(例) の上下の余白を詰める (最新のStreamlitはstCaptionContainer) */
        div[data-testid="stCaptionContainer"] {
            margin-top: -8px;    /* 質問文と例の間の余白 */
            margin-bottom: -8px; /* 例と入力欄の間の余白 */
            padding-top: 0;
        }
        /* 古いStreamlit (stCaption) */
        div[data-testid="stCaption"] {
            margin-top: -8px;    /* 質問文と例の間の余白 */
            margin-bottom: -8px; /* 例と入力欄の間の余白 */
            padding-top: 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # --- 質問、例、入力欄の順序を変更 ---
    
    # 質問1
    st.markdown("① 学習を通じて、最終的に「何ができるように」なりたいですか？")
    st.caption("例：英語の会議で自分の意見を述べられる、Pythonでデータ分析レポートを作成できる、簿記2級の試験に合格する")
    goal_what = st.text_input(
        "① 学習を通じて、最終的に「何ができるように」なりたいですか？", # st.text_inputにはlabelが必須のため内部的に設定
        key="goal_what_input",
        label_visibility="hidden", # ラベルを非表示にする
        placeholder="（ここに入力してください）" # 任意でプレースホルダーを追加
    )

    # グループ間の余白（仕切り）
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    # 質問2
    st.markdown("② いつまでに、その状態を目指しますか？")
    st.caption("例：3ヶ月後、次のプロジェクトが始まるまで、12月末の試験日")
    goal_when = st.text_input(
        "② いつまでに、その状態を目指しますか？",
        key="goal_when_input",
        label_visibility="hidden",
        placeholder="（ここに入力してください）"
    )

    # グループ間の余白（仕切り）
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    # 質問3
    st.markdown("③ 目標を「達成できた」と判断するための、具体的な行動や基準（合格ライン）を教えてください。")
    st.caption("例：模擬試験で90点以上取る、毎日30分コードを書き、週に1つアプリの機能を追加する、上司のレビューでOKをもらう")
    goal_criteria = st.text_input(
        "③ 目標を「達成できた」と判断するための、具体的な行動や基準（合格ライン）を教えてください。",
        key="goal_criteria_input",
        label_visibility="hidden",
        placeholder="（ここに入力してください）"
    )

    # ボタンの上の余白
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    
    # --- 変更ここまで ---

    if st.button("目標を送信", key="submit_button"):
        
        # 3つの入力欄がすべて入力されているかチェック
        if not goal_what or not goal_when or not goal_criteria:
            st.warning("すべての項目（①、②、③）に入力してください。")
        else:
            # すべて入力されている場合のみ、対話を開始する
            
            # ユーザー入力を統合したプロンプトを作成
            user_prompt = (
                f"私がこれから学習しようとしていることです。この情報に基づいて学習目標を設定できるよう、考えを深めるための質問をして、対話を通して支援してください。\n\n"
                f"① 何ができるようになりたいか: {goal_what}\n"
                f"② いつまで: {goal_when}\n"
                f"③ 達成基準: {goal_criteria}"
            )

            # ユーザープロンプトを履歴に追加
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            # API呼び出し用に履歴を整形
            history = [
                {"role": "user" if msg["role"] == "user" else "model", "parts": [{"text": msg["content"]}]} 
                for msg in st.session_state.messages
            ]
            
            # ヘルパー関数でAPIを呼び出す
            gemini_response = get_gemini_response_with_retry(history, SYSTEM_PROMPT)

            if gemini_response:
                # Geminiの応答を表示
                with st.chat_message("assistant"):
                    st.markdown(gemini_response)

                # Geminiの応答を履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": gemini_response})
                
                # チャット開始フラグを立てて再実行
                st.session_state.chat_started = True
                st.rerun()

def handle_ongoing_chat():
    """目標送信後の継続的なチャット対話を処理する"""
    # 既存のメッセージを表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 最終目標が確定していない場合のみチャット入力ボックスを表示
    if not st.session_state.finalized_goal:
        if prompt := st.chat_input("何が知りたいですか？"):
            # ユーザーの新しいプロンプトを履歴に追加して表示
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # API呼び出し用に履歴を整形
            history = [
                {"role": "user" if msg["role"] == "user" else "model", "parts": [{"text": msg["content"]}]} 
                for msg in st.session_state.messages
            ]

            # ヘルパー関数でAPIを呼び出す
            gemini_response = get_gemini_response_with_retry(history, SYSTEM_PROMPT)

            if gemini_response:
                # Geminiの応答を表示
                with st.chat_message("assistant"):
                    st.markdown(gemini_response)
                
                # Geminiの応答を履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": gemini_response})

                # 最終目標の形式が出力されたかチェックし、チャットを終了
                if "## あなたの学習目標が固まりましたね！" in gemini_response:
                    st.session_state.finalized_goal = True
                    st.rerun() 
                    st.stop()
    
    # 最終目標が確定 *した後* のロジック
    else:
        # 1. 注意書きを表示
        st.warning("設定した学習目標はページをリフレッシュすると消えてしまいますので、どこかにコピーアンドペーストして保存しておきましょう！")
        
        # 2. ダウンロードボタンとインストラクションのロジック
        st.info("目標の設定お疲れ様でした！次に今後の振り返りで使うテンプレートのダウンロードを行いましょう！")
        
        template_file_path = "templates/nikki4.docx"
        
        if os.path.exists(template_file_path):
            with open(template_file_path, "rb") as f:
                template_data = f.read()
            
            st.markdown("---")
            st.header("振り返り用テンプレートのダウンロード")

            # 3. ダウンロードボタンを先に表示
            st.download_button(
                label="📥 テンプレートをダウンロード",
                data=template_data,
                file_name="nikki4.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            # 4. インストラクションを後に表示
            st.markdown("""
**ダウンロード後のインストラクション**
1. 学習を行った日はこのテンプレートの設問に回答して、振り返りを行ってください
2. 書き終えたら、ファイルを保存しましょう
3. [対話用アプリ](https://learningmotivationchat.streamlit.app/)にアクセスし、ログイン(初回は新規登録)を行いましょう
4. 保存した当日の振り返りのファイルを、ログインした先のチャット画面でアップロードして対話を始めましょう
""")
        else:
            st.error(f"エラー: テンプレートファイル '{template_file_path}' が見つかりません。ファイル名とtemplatesフォルダの場所を確認してください。")

# --- Main App Execution ---

if not st.session_state.chat_started:
    handle_initial_goal_setting()
else:
    handle_ongoing_chat()
