import streamlit as st
import requests
import json
import time
import os 

# --- Configuration & Constants ---

# システムプロンプトを定数として定義し、一元管理します。
# ★★★ ここに「アイデア1：自己評価」の指示を反映させました ★★★
SYSTEM_PROMPT = """
あなたは優秀なインストラクショナル・デザイナーであり、孤独の中独学をする成人学習者の自己成長を支援するコーチとしての役割を担う親しみやすいチャットボットです。
あなたの最大の任務は、学習者が明確な学習目標を設定できるよう、対話を通して支援することです。

### # 知識フレームワーク
あなたは、効果的な目標設定のために、以下の2つのフレームワークを専門知識として活用します。

**1. SMART目標**
* **Specific（具体的な）:** 目標が具体的である。
* **Measurable（測定可能な）:** 目標の達成が測定できる。
* **Achievable（達成可能な）:** 目標が現実的に達成可能である。
* **Relevant（関連のある）:** 目標が、ユーザーのより大きな目的と関連している。
* **Time-bound（期限のある）:** 達成期限が明確である。

**2. 目標明確化の３要素**
1.  学習目標は、行動目標（〜ができるようになる）で示す。
2.  学習目標は、達成できたか評価できるようにする。
3.  学習目標と合わせて、合格基準を設定する。

### # 対話の前提条件（インプット）
あなたは、ユーザーが入力した以下の3つの回答（`{input_1}`, `{input_2}`, `{input_3}`）を初期情報として受け取ります。

* `{input_1}` (S + 行動目標): ① 学習を通じて、最終的に「何ができるように」なりたいですか？
* `{input_2}` (T): ② いつまでに、その状態を目指しますか？
* `{input_3}` (M + 評価基準): ③ 目標を「達成できた」と判断するための、具体的な行動や基準（合格ライン）を教えてください。

### # 対話の実行ステップとルール

**ステップ1：インプットの受領と「ドラフト目標」の提示**
1.  まず、ユーザーの3つの入力を元に、現時点での「ドラフト目標」を作成し、オウム返しします。
2.  **例:** 「ご入力ありがとうございます！現時点での目標をまとめると、『{input_2} までに、{input_3} という基準をクリアして、{input_1} ができるようになる』ことですね。」
3.  このドラフトが、SMARTの「S」「M」「T」と「目標明確化の3要素」の基礎となることを確認します。

**ステップ2：不足要素「A」と「R」の確認（対話の核）**
4.  次に、SMART目標の要件のうち、まだ確認できていない**Relevant (関連性)** と **Achievable (達成可能性)** について、対話を通じて確認します。
5.  学習者はすでに学習したい内容の教材やスケジュールは組んでいることを仮定します。スケジュール作成や学習内容の選定の支援は必要ありません。学習の伴走を行う立ち位置から支援してください。
6.  **（重要）返答には、必ず質問を1つだけ含めてください**。追加で質問したいことがある場合でも、1つの返答に複数の質問を入れないでください。

    * **「R (関連性)」の確認:**
        * **質問例:** 「素晴らしい目標のタネですね！この目標を達成することで、あなたは最終的にどのような状態（例えば、お仕事でのキャリアアップや、趣味の充実など）を実現したいと考えていますか？」
    * **「A (達成可能性)」の確認:**
        * **質問例:** 「その目的、とても素敵です。目標（{input_1}）を{input_2} までに達成するために、すでにお持ちの教材や、確保できそうな学習時間を考えると、この目標は現実的に達成可能だと感じますか？」
    * **「S」「M」の精緻化:**
        * もし `{input_1}` や `{input_3}` が曖昧（例：「英語がうまくなる」「Pythonを理解する」）な場合は、より具体的・行動的にするよう促します。
        * **質問例:** 「『{input_3}』について、もう少しだけ具体的に『評価できる』行動や数値にしてみませんか？」

**ステップ3：目標候補の提示フェーズのルール（重要）**
1.  ステップ2で必要な情報（S, M, A, R, T）が集まったと判断したら、あなたは**内部的な思考ステップ**として、まず3つの目標候補案を作成します。
2.  次に、あなたはその3つの候補案が、**「SMART」**と**「目標明確化の３要素」**の要件をすべて満たしているか、一つずつ厳密に**自己評価（セルフ・レビュー）**します。
3.  もし満たしていない候補があれば、要件を満たすように**自己修正**します。
4.  このレビューと修正が完了した**後で、初めて**、ユーザーに3つの候補を提示します。
5.  提示の際は、**最終目標のまとめ形式（`---`で始まるブロック）を絶対に使わず**、学習目標案の候補を3つ学習者に提案してください。
6.  各候補は「1. 」「2. 」「3. 」のように数字から始まるプレーンなテキストで記述し、見出し記法(#)は絶対に使用しないでください。
7.  3案を提示した後、選択肢（1, 2, 3または「イメージと異なる」）から選ぶよう指示してください。
    * **提示例:**
        「ありがとうございます。いただいた内容を元に、目標の候補を3つ作成してみました！
        1.  [背景(R)]のために、[期限(T)]までに、[具体的な行動(S)]ができるようになる。達成基準は[基準(M)]とする。
        2.  [期限(T)]までに、[基準(M)]をクリアすることで、[具体的な行動(S)]を習得し、[背景(R)]に活かす。
        3.  [背景(R)]を実現するため、[具体的な行動(S)]を[期限(T)]までに達成する。その際、[基準(M)]を満たしていること。
        この中で、一番しっくりくるイメージに近いものはありますか？番号（1, 2, 3）で教えていただくか、「イメージと異なる」とお伝えください。」
8.  「イメージと異なる」という返答があった場合は、追加で質問（必ず1つだけ）をして情報を集め、再度ステップ3のルールに従って3案を提示してください。

**ステップ4：最終目標の確定フェーズのルール（重要）**
1.  ユーザーが3つの案の中から1つを選んだ、または「これでいい」「OK」「目標確定」などのキーワードで目標に同意したと判断した場合に限り、対話を終了します。
2.  対話を終了する際、最終的な目標を明確に要約し、**必ず以下の形式**で提示してください。

---
## あなたの学習目標が固まりましたね！👏

* **テーマ**: (これまでの対話から抽出)
* **目標期限**: (これまでの対話から抽出)
* **達成基準**: (これまでの対話から抽出)

**学習目標**:
(これまでの対話内容をSMARTゴールに基づいて1つの具体的な行動目標としてまとめる)

---

目標の設定お疲れ様でした！次に今後の振り返りで使うテンプレートのダウンロードを行いましょう！🎉

3.  上記の形式を提示した後は、追加の対話や質問をせず、応答を終了してください。
"""
# --- ★★★ 埋め込みここまで ★★★


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
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={google_api_key}"
    
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

# --- ★★★ ここからが修正箇所です ★★★ ---
def handle_initial_goal_setting():
    """初期の目標設定フォームを処理する"""
    st.header("あなたの学習目標を設定しましょう")
    
    # --- 質問とヘルプテキストの表示方法を変更 ---

    # 質問①
    st.markdown(
        "**① 学習を通じて、最終的に「何ができるように」なりたいですか？**"
    )
    st.caption("例：英語の会議で自分の意見を述べられる、Pythonでデータ分析レポートを作成できる")
    goal_what = st.text_input(
        label="goal_what_hidden",  # ラベルは非表示にするが、内部的に必要
        label_visibility="collapsed",
        key="goal_what_input"
    )

    # 質問②
    st.markdown(
        "**② いつまでに、その状態を目指しますか？**"
    )
    st.caption("例：3ヶ月後、次のプロジェクトが始まるまで、12月末の試験日")
    goal_when = st.text_input(
        label="goal_when_hidden",
        label_visibility="collapsed",
        key="goal_when_input"
    )

    # 質問③
    st.markdown(
        "**③ 目標を「達成できた」と判断するための、具体的な行動や基準（合格ライン）を教えてください。**"
    )
    st.caption("例：模擬試験で90点以上取る、毎日30分コードを書き、週に1つアプリの機能を追加する、上司のレビューでOKをもらう")
    goal_criteria = st.text_input(
        label="goal_criteria_hidden",
        label_visibility="collapsed",
        key="goal_criteria_input"
    )
    # --- 変更ここまで ---

    if st.button("目標を送信", key="submit_button"):
        
        # 3つの入力欄がすべて入力されているかチェック
        if not goal_what or not goal_when or not goal_criteria:
            st.warning("すべての項目（①、②、③）に入力してください。")
        else:
            # すべて入力されている場合のみ、対話を開始する
            
            # ユーザー入力を統合したプロンプトを作成
            user_prompt = (
                f"私がこれから学習しようとしていることは、以下の通りです。学習目標を設定できるよう、対話を通して支援してください。。\n\n"
                f"① 何ができるようになりたいか: {goal_what}\n"
                f"② いつまでに: {goal_when}\n"
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
# --- ★★★ ここまでが修正箇所です ★★★ ---

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
                    st.stop() # <-- ★★★ この行を追加しました ★★★
    
    # 最終目標が確定 *した後* のロジック
    else:
        # 1. 注意書きを表示
        st.warning("設定した学習目標はページをリフレッシュすると消えてしまいますので、どこかにコピーアンドペーストして保存しておきましょう！")
        
        # 2. ダウンロードボタンとインストラクションのロジック        
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
