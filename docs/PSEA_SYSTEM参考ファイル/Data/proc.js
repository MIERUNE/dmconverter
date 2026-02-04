/// Copyright (C)2009 GSI. All Rights Reserved. 
var ClassGSI_PublicSurvey = {
 Name	: "公共測量成果検査支援ツール"
,Last	: "2009.03.04"
,Ver	: "0.9.1.00003"
};
/* ---------------------------------------------------------------------------------------------*
 * class
 *  var obj = new GSI_PublicSurvey();
 * .............................................................................................
 * include
 *  mod_common.js
 *  mod_data.js
 */
function GSI_PublicSurvey(){
  /* -------------------------------------------------------------------------------------------*
   * Private
   * -------------------------------------------------------------------------------------------*/  
  this.fModeEvt   = 2;                                    // 1:onkeyup, 2:onclick

  /* -------------------------------------------------------------------------------------------*
   * Private Object Class
   * -------------------------------------------------------------------------------------------*/  
  this.objCom     = null;                                 // Class

  /* -------------------------------------------------------------------------------------------*
   * Private Valuable
   * -------------------------------------------------------------------------------------------*/
  // フラグ
  this.fLoad      = false;                                // フラグ：初期ロード
  // クラス
  this.oData      = null;                                 // クラス：データ
  // オブジェクト
  this.iDiv       = "dForm";      this.oDiv       = null; // ページ
  this.iDivDInput = "dInput";     this.oDivDInput = null; // ページ：入力
  this.iDivDSheet = "dSheet";     this.oDivDSheet = null; // ページ：シート
  this.iDivDPrint = "dPrint";     this.oDivDPrint = null; // ページ：印刷

  this.iBT_Sheet  = "iBTSheet";   this.oBT_Sheet  = null; // ページ：シート：ボタン
  
  // メッセージ
  this.MsgNess              = "<span style=\"color:#F26027;\">【 必須 】 </span>";
  this.MsgSheetDefMainName  = "測量計画機関名を入力して下さい。\n";
  this.MsgSheetDefMainType  = "作業種別を選択して下さい。\n";
  this.MsgSheetMainName     = this.MsgSheetDefMainName;
  this.MsgSheetMainType     = this.MsgSheetDefMainType;
  
  // 値
  this.vMainName  = "";
  this.vMainCode  = "";
  this.vMainWork  = new Array();
  this.vSheetList = new Array();
  
  /* -------------------------------------------------------------------------------------------*
   * コンストラクタ 
   * -------------------------------------------------------------------------------------------*/
  // コンストラクタ
  GSI_PublicSurvey.prototype.Constructor = function(){
    this.objCom = new com();
    this.oDiv   = this.objCom.Object(this.iDiv);
    if(this.oDiv != null){
      this.oData = new GSI_PublicSurveyData();
      this.fLoad = true; 
      this.ConstructorStyle("Input");
    }
  };


  /* コンストラクタ：タイプ
   * arg
   *  string type : スタイルタイプ
   *                Input : 入力
   *                Print : 印刷
   */
  GSI_PublicSurvey.prototype.ConstructorStyle = function(type){
    if(type == "Input"){
      document.title                      = "公共測量成果：検査支援";
      document.body.style.margin          = "10px";
      document.body.style.fontSize        = "12px";
      document.body.style.backgroundColor = "#F6FCF1";
    }
    else if(type == "Print"){
      document.title                      = "公共測量成果：成果提出確認シート";
      document.body.style.margin          = "10px";
      document.body.style.fontSize        = "14px";
      document.body.style.backgroundColor = "#FFFFFF";
    }
  };

  /* -------------------------------------------------------------------------------------------*
   * Class Public：表示切替
   * -------------------------------------------------------------------------------------------*/
  /* 表示切替
   * arg
   *  string iMark : Div マーク
   *  string vMark : タイトル
   *  string iBody : Div 内容
   *  string vSW   : 強制スイッチ
   */
  GSI_PublicSurvey.prototype.Disp = function(iMark, vMark, iBody, vSW){
    var oMark = this.objCom.Object(iMark);
    var oBody = this.objCom.Object(iBody);
    
    var sw = vSW;
    if(!this.objCom.ObjectDVal(vSW)){
      sw  = "block";
      if(oBody.style.display == "block"){
        sw  = "none";
      }
    }
    oMark.innerHTML = "" + "<img src=\"iMark_" + sw + ".png\" alt=\"\" />" + " " + vMark;
    oBody.style.display = sw;
  };

  /* 表示切替：タイプ
   * arg
   *  string nType : 処理タイプ
   * [string vSW  ]: 強制スイッチ
   */
  GSI_PublicSurvey.prototype.DispType = function(nType, vSW){
    var iMark = "";
    var vMark = "";
    var iBody = "";
    
    if(nType == "1"){
      iMark = "fTypeMark";
      vMark = "検査支援";
      iBody = "fType";
    }
    else if(nType == "2"){
      iMark = "fSheetMark";
      vMark = "成果提出確認シート";
      iBody = "fSheet";
    }
    else if(nType == "3"){
      if(!this.objCom.ObjectDVal(vSW)){
        vSW = "none";
      }
      var vSWInput = "block";
      if(vSW == "block"){
        vSWInput = "none";
        this.ConstructorStyle("Print");
      }
      else{
        this.ConstructorStyle("Input");
      }
      
      this.oDivDInput.style.display = vSWInput;
      this.oDivDSheet.style.display = vSWInput;
      this.oDivDPrint.style.display = vSW;
    }
    
    if(iMark != "" && vMark != "" && iBody != ""){
      this.ConstructorStyle("Input");
      this.DispType("3", "none");
      this.Disp(iMark, vMark, iBody, vSW);
    }
    this.DispBTSheetSrc();
  };

  /* 表示切替：確認ボタン
   * arg
   *  string type  : 処理タイプ
   *                 iMainName
   *                 iMainType
   *  string value : 値
   */
  GSI_PublicSurvey.prototype.DispBTSheet = function(type, value){
    if(type == "iMainName"){
      this.MsgSheetMainName = this.MsgSheetDefMainName;
      if(value != null && value != ""){
        this.MsgSheetMainName = "";
      }
    }
    else if(type == "iMainType"){
      this.MsgSheetMainType = this.MsgSheetDefMainType;
      if(value != null && value.length > 0){
        this.MsgSheetMainType = "";
      }              
    }
    
    this.DispBTSheetSrc();
  };
  
  // 表示切替：確認ボタン：イメージ
  GSI_PublicSurvey.prototype.DispBTSheetSrc = function(type, value){
    if(this.oBT_Sheet != null){
      if(this.fModeEvt == 1){
        if(this.MsgSheetMainName == ""){
          this.oBT_Sheet.src = "iBT_sheet.png";
        }
        else{
          this.oBT_Sheet.src = "iBT_sheet_disabled.png";
        }
      }
      else{
        this.oBT_Sheet.src = "iBT_sheet.png";
      }
    }
  };
 
  /* -------------------------------------------------------------------------------------------*
   * Class Public：ページ
   * -------------------------------------------------------------------------------------------*/
  // ページ：メイン
  GSI_PublicSurvey.prototype.Page = function(){
    if(this.fLoad){    
      var n     = 0;
      var dHTML = "";
  
      // 入力    
      dHTML += "<div id=\"" + this.iDivDInput + "\" style=\"display:block;\">";
        // 申請確認支援
        dHTML += "<div id=\"fTypeMark\" style=\"cursor:pointer;font-size:20px;\" onclick=\"oGSI_PublicSurvey.DispType('1');\"></div>";
        
        dHTML += "<div id=\"fType\" style=\"display:none;border:dotted 3px #408707;background-color:#EAF9DE;\">";
          dHTML += "<table border=\"0\" cellspacing=\"5\" colspacing=\"0\">";
            dHTML += "<tr>";
              dHTML += "<td>";
                dHTML += "「成果提出確認シート」<br />";
                dHTML += "本ツールでは、作業種別毎の成果等について確認をしていただくことができます。<br />";
                dHTML += "<br />";
                
                var Evt2 = "";
                if(this.fModeEvt == 1){
                  Evt2 = " onkeyup=\"oGSI_PublicSurvey.DispBTSheet('iMainName', this.value);\" ";
                }

                dHTML += "１．" + this.MsgNess + "測量計画機関名を入力して下さい。<br />";
                dHTML += "<input type=\"text\" id=\"iMainName\" style=\"width:200px;ime-mode:active;\" " + Evt2 + " /><br />";
                dHTML += "<br />";

                dHTML += "２．助言番号を入力して下さい。（全角入力も可能）<br />";
                dHTML += "<input type=\"text\" id=\"iMainCode\" style=\"width:200px;ime-mode:disabled;\" /><br />";
                dHTML += "<br />";

                dHTML += "３．" + this.MsgNess + "作業種別<br />";
                dHTML += "<div id=\"" + this.iDivWork + "\" style=\"margin:5px 0px 00px 15px;\">";
                  dHTML += "作業種別を選択してください。（複数選択可能）<br />";
                  dHTML += "<div style=\"border:solid 1px #408707;background-color:#F2F9ED;\">";
                  
                  var dWork = this.oData.dWork();
                  var nWork = 0;
                  for(n = 0; n < dWork.length; n++){
                    if(dWork[n] == "-"){
                      dHTML += "<table border=\"0\" collspacing=\"0\" cellspacing=\"0\" style=\"width:100%;\"><tr><td style=\"border-bottom:dotted 1px #408707;\"><img src=\"1.1px.png\" alt=\"\" /></td></tr></table>";
                    }
                    else{
                      dHTML += "<input type=\"checkbox\" id=\"iWork" + nWork + "\" value=\"" + dWork[n] + "\" /> " + dWork[n] + "<br />";
                      nWork++;
                    }
                  }
                  dHTML += "</div>";
                dHTML += "</div>"; 
                
                dHTML += "<img src=\"iBT_sheet_disabled.png\" id=\"" + this.iBT_Sheet + "\" style=\"cursor:pointer;margin:10px;\" onclick=\"oGSI_PublicSurvey.PageSheet();\" alt=\"\" />";                
              dHTML += "</td>";
            dHTML += "</tr>";
          dHTML += "</table>";
        dHTML += "</div>";
      dHTML += "</div>";

      // 成果提出確認シート
      dHTML += "<div id=\"" + this.iDivDSheet + "\" style=\"display:none;\"></div>";

      // 印刷
      dHTML += "<div id=\"" + this.iDivDPrint + "\" style=\"display:none;\"></div>";

      this.oDiv.innerHTML = dHTML;
      
      // Object
      this.oDivDInput = this.objCom.Object(this.iDivDInput);
      this.oDivDSheet = this.objCom.Object(this.iDivDSheet);
      this.oDivDPrint = this.objCom.Object(this.iDivDPrint);
      this.oBT_Sheet = this.objCom.Object(this.iBT_Sheet);
      this.DispBTSheetSrc();
      
      // Display
      this.DispType('1', 'block');
    }
  };
  
  // ページ：確認シート
  GSI_PublicSurvey.prototype.PageSheet = function(nType){
    var n     = 0;
    var dHTML = "";
    
    // 値取得
    var oMainName   = this.objCom.Object("iMainName");
    var oMainCode   = this.objCom.Object("iMainCode");
    
    this.vMainName   = oMainName.value;
    this.vMainCode   = oMainCode.value;
    
    this.vMainWork = new Array();
    for(n = 0; ; n++){
      var oWork = this.objCom.Object("iWork" + n);
      if(oWork != null){
        if(oWork.checked){
          this.vMainWork.push(oWork.value);
        }
      }
      else{
        break;
      }
    }

    var msg = "";
    if(this.fModeEvt == 2){
      this.DispBTSheet('iMainName', this.vMainName);
      this.DispBTSheet('iMainType', this.vMainWork);
    }

    // 確認シート
    if(this.MsgSheetMainName != ""){
      if(this.MsgSheetMainName != ""){
        msg += "・" + this.MsgSheetMainName;
      }
    }
    if(this.MsgSheetMainType != ""){
      if(this.MsgSheetMainType != ""){
        msg += "・" + this.MsgSheetMainType;
      }    
    }
    
    if(msg != ""){
      alert(msg);
    }
    else{
      dHTML += "<div id=\"fSheetMark\" style=\"cursor:pointer;font-size:20px;\" onclick=\"oGSI_PublicSurvey.DispType('2');\"></div>";

      dHTML += "<div id=\"fSheet\" style=\"display:none;border:dotted 3px #408707;background-color:#EAF9DE;\">";
        dHTML += "<table border=\"0\" cellspacing=\"5\" colspacing=\"0\">";
          dHTML += "<tr>";
            dHTML += "<td>";

              dHTML += "<table border=\"0\" cellspacing=\"0\" colspacing=\"0\">";
                dHTML += "<tr>";
                  dHTML += "<td>測量計画機関</td>";
                  dHTML += "<td>：" + this.vMainName + "</td>";
                dHTML += "</tr>";
                dHTML += "<tr>";
                  dHTML += "<td>助言番号</td>";
                  dHTML += "<td>：" + this.vMainCode + "</td>";
                dHTML += "</tr>";
              dHTML += "</table>";
              dHTML += "<br />";
              
              for(n = 0; n < this.vMainWork.length; n++){
                if(n == 0){
                  dHTML +="作業種別：<br />";
                }
                dHTML += "　・ " + this.vMainWork[n] + "<br />";
              }
              dHTML += "<br />";
              
              var fWork = false;
              dHTML += "<table border=\"0\" cellpadding=\"2\" colspacing=\"0\" style=\"border-collapse:collapse;\">";
                
                this.vSheetList = new Array();
                var dSheet = this.oData.dSheet(this.vMainWork);
                for(n = 0; n < dSheet.Name.length; n++){
                  if(n == 0){
                    fWork = true;
                    dHTML += "<tr>";
                      dHTML += "<td style=\"text-align:center;border:solid 1px #408707;background-color:#91C58B;text-align:center;\">項目</td>";
                      dHTML += "<td style=\"text-align:center;border:solid 1px #408707;background-color:#91C58B;text-align:center;\">確認</td>";
                    dHTML += "</tr>";                  
                  }
                  
                  this.vSheetList.push(dSheet.Name[n]);
                  
                  dHTML += "<tr>";
                    dHTML += "<td style=\"border:solid 1px #408707;background-color:#F2F9ED;\">" + dSheet.Name[n]  + "</td>";
                    dHTML += "<td style=\"border:solid 1px #408707;background-color:#F2F9ED;text-align:center;\"><input type=\"checkbox\" id=\"iSheetList" + n + "\" value=\"" + dSheet.Name[n] + "\" /></td>";
                  dHTML += "</tr>";                  
                };
                
              dHTML += "</table>";      
              
              dHTML += "<br />";
              
              dHTML += "<img src=\"iBT_print.png\" style=\"cursor:pointer;\" onclick=\"oGSI_PublicSurvey.PageSheetPrint();\" alt=\"\" />";

            dHTML += "</td>";
          dHTML += "</tr>";
        dHTML += "</table>";      
      dHTML += "</div>";

      this.oDivDSheet.innerHTML = dHTML;
      
      // Display
      this.DispType('1', 'none');
      this.DispType('2', 'block');
    }
  };
  
  // ページ：確認シート
  GSI_PublicSurvey.prototype.PageSheetPrint = function(nType){
    if(window.confirm("印刷しますか？\n印刷後、申請確認支援に戻りたい場合、表題の「成果提出確認シート」の文字をクリックして下さい。\n")){
      var FontSize = "14px";
      
      this.DispType("3", "block");
    
      var dHTML = "";
      
      var dDate = new Date();
      var cDate = dDate.getFullYear() + "/" + (dDate.getMonth() + 1) + "/" + dDate.getDate();
      
      dHTML += "<div style=\"font-size:" + FontSize + ";width:800px;\">";
        dHTML += "<table border=\"0\" cellpadding=\"5\" cellspacing=\"0\" style=\"width:100%;\">";
          dHTML += "<tr>";
            dHTML += "<td style=\"font-size:" + FontSize + ";text-align:right;\">" + cDate + "</td>";
          dHTML += "</tr>";
          dHTML += "<tr>";
          dHTML += "</tr>";
            dHTML += "<td style=\"font-size:" + FontSize + ";text-align:center;\"><div style=\"cursor:pointer;\" onclick=\"oGSI_PublicSurvey.PageSheetPrintClose();\"/>成果提出確認シート</div></td>";
          dHTML += "<tr>";
          dHTML += "</tr>";
            dHTML += "<td style=\"font-size:" + FontSize + ";text-align:left;\">";
              // 計画機関
              dHTML += "測量計画機関　" + this.vMainName + "<br />";
              // 助言番号
              dHTML += "助言番号　" + this.vMainCode + "<br />";
              
              // 作業・作業種別
              for(n = 0; n < this.vMainWork.length; n++){
                if(n == 0){
                  dHTML +="作業種別：<br />";
                }
                dHTML += "　" + this.vMainWork[n] + "<br />";
              }
              dHTML += "<br />";
              
              // 提出物・未確認
              var c0 = "";
              var c1 = "";
              var nSheetList = 0;
              for(nSheetList = 0; nSheetList < this.vSheetList.length; nSheetList++){
                var o = this.objCom.Object("iSheetList" + nSheetList);
                if(o == null){
                  break;
                }
                var v = "　・ " + this.vSheetList[nSheetList] + "<br />";
                if(o.checked){
                  c1 += v;
                }
                else{
                  c0 += v;
                }
              }
              
              if(c1 != ""){
                dHTML += "提出物<br />";
                dHTML += c1;
                dHTML += "<br />";
              }
              if(c0 != ""){
                dHTML += "未確認<br />";
                dHTML += c0;
              }
            dHTML += "</td>";
          dHTML += "</tr>";
        dHTML += "</table>";
      dHTML += "</div>";
      
      this.oDivDPrint.innerHTML = dHTML;
      
      // Dirplay
      this.DispType("3", "block");

      // Print
      window.print();
    }
  };
    
  // ページ：確認シート：閉じる
  GSI_PublicSurvey.prototype.PageSheetPrintClose = function(){
    this.DispType("3", "none");
  };
  
  // Constractor
  this.Constructor();
};

/* ---------------------------------------------------------------------------------------------*
 * Main
 * ---------------------------------------------------------------------------------------------*/
// Class
var oGSI_PublicSurvey     = null;

/* ---------------------------------------------------------------------------------------------*
 * Main Event：onUnload
 * ---------------------------------------------------------------------------------------------*/
// Event : onload
window.onload = function(){
  oGSI_PublicSurvey = new GSI_PublicSurvey();
  oGSI_PublicSurvey.Page();
};