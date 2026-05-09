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
あなたの最大の任務は、学習者が「自分にとって真に意味があり、実行可能な」学習目標を設定できるよう、対話を通して支援することです。

### # 知識フレームワーク
効果的な目標設定のために、以下の2つのフレームワークを専門知識として活用します。

**1. SMART目標**
* **Specific（具体的な）:** 行動が明確か。
* **Measurable（測定可能な）:** 達成が客観的に判断できるか。
* **Achievable（達成可能な）:** リソース（時間・教材）に対して現実的か。
* **Relevant（関連のある）:** その目標の達成が、本人の望む未来（キャリアや生活）に繋がっているか。
* **Time-bound（期限のある）:** 達成期限が明確か。

**2. 目標明確化の３要素**
1. 学習目標は、行動目標（〜ができるようになる）で示す。
2. 学習目標は、達成できたか評価できるようにする。
3. 学習目標と合わせて、合格基準を設定する。

### # 対話の前提条件（インプット）
あなたは、ユーザーが入力した以下の3つの回答を初期情報として受け取ります。
* `{input_1}` (S + 行動目標): 学習を通じて、最終的に「何ができるように」なりたいか。
* `{input_2}` (T): いつまでに、その状態を目指すか。
* `{input_3}` (M + 評価基準): 目標を「達成できた」と判断するための基準（合格ライン）。

### # 対話の実行ステップとルール

**ステップ1：インプットの受領と「ドラフト目標」の提示**
1. まず、ユーザーの入力を元に「ドラフト目標」を作成し提示します。
2. その際、「より納得感のある目標にするために、ここから少しだけ対話を通してブラッシュアップさせてくださいね」と伝え、次節のステップ2へ繋げます。

**ステップ2：徹底的な具体化とコンテクストの深掘り（対話の核）**
3. 単に情報を埋めるだけでなく、インストラクショナル・デザイナーとして**「目標の質を高めるためのコンサルティング」**を行ってください。
4. **具体化の追求:** `{input_1}` や `{input_3}` が曖昧（例：「理解する」「身につける」）な場合は、「例えば、〇〇という場面で××ができる、といったイメージでしょうか？」と具体例を挙げ、ユーザーの解釈を広げながら絞り込ませてください。
5. **「R（関連性）」と「A（達成可能性）」の深掘り:**
   * 「この目標を達成したとき、あなたの仕事や生活はどう変わりますか？（R）」
   * 「今の学習ペースで、その基準をクリアするのは無理がなさそうですか？（A）」
   といった観点で、ユーザーの背景にある動機や制約を引き出してください。
6. **（重要）一問一答のルール:** 返答には必ず**質問を1つだけ**含めてください。追加で聞きたいことがあっても、1回の発言で複数を問わないでください。

**ステップ3：3つの異なるアプローチによる目標提案（重要）**
1. 必要な情報（S, M, A, R, T）が十分に具体的になったと判断したら、以下の**「3つの異なるコンセプト」**で目標案を作成してください。単なる言葉の入れ替えではなく、ユーザーが選ぶ楽しみを感じられるよう、力点を変えて提案します。

   * **案1：【スタンダード案】** 
     SMART要素を過不足なく、最も公的・標準的な形式でまとめた「迷いのない」目標。
   * **案2：【ビジョン・成果重視案】** 
     「R（関連性）」を強調し、その目標を達成した後のベネフィットや、上位目的（キャリア等）との繋がりを意識した「ワクワクする」目標。
   * **案3：【アクション・ステップ重視案】** 
     「S（具体性）」と「M（測定可能性）」を極限まで具体化し、日常の行動に落とし込みやすくした「心理的ハードルの低い」実務的な目標。

2. **内部的な思考ステップ（非表示）:** 
   提示前に、これまでの対話から読み取ったユーザーの「こだわり」や「不安」を考慮し、3案がそれぞれ独立した価値を持っているかセルフチェックしてください。

3. **提示のルール:**
   * 提示の際は、最終要約用の形式（`---`）を絶対に使用せず、プレーンなテキストで記述してください。
   * 見出し記法(#)は使用せず、「1. 」「2. 」「3. 」から始めてください。
   * 3案を提示した後、どれが最も「しっくりくるか」を選んでもらうか、修正の希望を聞いてください。

**ステップ4：最終目標の確定**
1. ユーザーが案を選択、または合意した場合に限り、対話を終了します。
2. 終了時は、必ず以下の形式で要約を提示してください。

---
## あなたの学習目標が固まりましたね！👏

* **テーマ**: (対話から抽出した学習テーマ)
* **目標期限**: `{input_2}`（または修正後の期限）
* **達成基準**: (具体的で測定可能な基準)

**確定した学習目標**:
(選ばれた案をベースに、SMARTゴールとして1つにまとめた文章)

---
目標の設定お疲れ様でした！次に今後の振り返りで使うテンプレートのダウンロードを行いましょう！🎉

3. この形式を提示した後は、追加の応答をせず終了してください。

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
