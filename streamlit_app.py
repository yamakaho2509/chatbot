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
                    
                    # --- ▼▼▼ ここからが今回の追加修正 ▼▼▼ ---
                    # 最終目標の形式が出力された場合、保存を促す警告を表示
                    if "## あなたの学習目標が固まりましたね！" in gemini_response:
                        st.warning("設定した学習目標はページをリフレッシュすると消えてしまいますので、どこかにコピーアンドペーストして保存しておきましょう！")
                    # --- ▲▲▲ ここまでが今回の追加修正 ▲▲▲ ---
                        
                    st.markdown(gemini_response)
                
                # Geminiの応答を履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": gemini_response})

                # 最終目標の形式が出力されたかチェックし、チャットを終了
                if "## あなたの学習目標が固まりましたね！" in gemini_response:
                    st.session_state.finalized_goal = True
                    st.rerun() # 状態が変更されたら再実行してダウンロードボタンを表示
    else:
        # --- ダウンロードボタンのロジック (前回の修正を反映済み) ---
        st.info("目標の設定お疲れ様でした！次に今後の振り返りで使うテンプレートのダウンロードを行いましょう！")
        
        template_file_path = "templates/nikki4.docx"
        
        if os.path.exists(template_file_path):
            with open(template_file_path, "rb") as f:
                template_data = f.read()
            
            st.markdown("---")
            st.header("振り返り用テンプレートのダウンロード")

            # 1. ダウンロードボタンを先に表示
            st.download_button(
                label="📥 テンプレートをダウンロード",
                data=template_data,
                file_name="nikki4.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            # 2. インストラクションを後に表示
            st.markdown("""
**ダウンロード後のインストラクション**
1. 学習を行った日はこのテンプレートの設問に回答して、振り返りを行ってください
2. 書き終えたら、ファイルを保存しましょう
3. [対話用アプリ](https://learningmotivationchat.streamlit.app/)にアクセスし、ログイン(初回は新規登録)を行いましょう
4. 保存した当日の振り返りのファイルを、ログインした先のチャット画面でアップロードして対話を始めましょう
""")
        else:
            st.error(f"エラー: テンプレートファイル '{template_file_path}' が見つかりません。ファイル名とtemplatesフォルダの場所を確認してください。")
