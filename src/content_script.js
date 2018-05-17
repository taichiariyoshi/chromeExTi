//----------------------
$(function () {
    let flag = false;
    setInterval(function () {
        document.title = (flag ? "■" : "◆") + document.title.replace(/^[■◆]/, '');
        flag = !flag;
    }, 1000);
    //↑疎通確認コード
})

//pouupのテスト用
$(function(){
  $("#btn").click(function(){
    alert("!!!");
  });
});

//$(function(AutoClick){
//    document.getElementById("start!").onclick = function(AutoClick);
//})

//ボタンクリックでfunction発動
    //ボタンはhtmlのbuttonかPageAction
        //処理はbackgroundかpopupのイベントページで

//（処理）
    //likeボタンを連打
        //1からエラー"もうlikeがありません"のポップアップが出るまで
        //（if)マッチング→ポップアップ内の"あとでメッセージ"をクリックして連打処理に戻る
