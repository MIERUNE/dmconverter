/// Copyright (C)2009 GSI. All Rights Reserved. 
var ClassGSI_PublicSurveyData = {
 Name	: "公共測量成果検査支援ツール：データ"
,Last	: "2009.03.04"
,Ver	: "0.9.1.00003"
};
/* ---------------------------------------------------------------------------------------------*
 * class
 *  var obj = new GSI_PublicSurveyData();
 */
function GSI_PublicSurveyData(){

  /* -------------------------------------------------------------------------------------------*
   * Private Valuable
   * -------------------------------------------------------------------------------------------*/
  this.dWorkType        = new Array(); // 作業種別

  this.dSheetListType   = new Array(); // 確認シート：作業種別
  this.dSheetListName   = new Array(); // 確認シート：名称

  /* -------------------------------------------------------------------------------------------*
   * コンストラクタ 
   * -------------------------------------------------------------------------------------------*/
  // コンストラクタ
  GSI_PublicSurveyData.prototype.Constructor = function(){
  
    /* ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★*
     *
     * データ入力開始
     * 　　　↓
     * ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★*/
    // データ　＝　作業種別
    // 「-] は、セパレート
    this.dWorkType.push("基準点測量");
    this.dWorkType.push("水準測量");
    this.dWorkType.push("復旧測量（基準点）");
    this.dWorkType.push("復旧測量（水準点）");
    this.dWorkType.push("-");
    this.dWorkType.push("現地測量");
    this.dWorkType.push("空中写真測量（標定点設置）");
    this.dWorkType.push("空中写真測量（対空標識の設置）");
    this.dWorkType.push("空中写真測量（撮影（空中写真数値化））");
    this.dWorkType.push("空中写真測量（刺針）");
    this.dWorkType.push("空中写真測量（現地調査）");
    this.dWorkType.push("空中写真測量（空中三角測量）");
    this.dWorkType.push("空中写真測量（数値図化）");
    this.dWorkType.push("空中写真測量（補測編集）");
    this.dWorkType.push("既成図数値化（空中三角測量）");
    this.dWorkType.push("修正測量");
    this.dWorkType.push("写真地図の作成");
    this.dWorkType.push("航空レーザ測量");
    this.dWorkType.push("地図編集");
    this.dWorkType.push("基盤地図情報");
    this.dWorkType.push("-");
    this.dWorkType.push("路線測量");
    this.dWorkType.push("河川測量");
    this.dWorkType.push("用地測量");
    this.dWorkType.push("その他の応用測量");
 
    // データ　＝　確認シート
    var vType = "";
    // 確認名
    vType = "基準点測量";
　　this.dSheetList(vType, "観測手簿");
　　this.dSheetList(vType, "観測記簿");
　　this.dSheetList(vType, "計算簿");
　　this.dSheetList(vType, "平均図");
　　this.dSheetList(vType, "成果表");
　　this.dSheetList(vType, "点の記");
　　this.dSheetList(vType, "建標承諾書");                 // 自分の管理地に設置するケース大
　　this.dSheetList(vType, "測量標設置位置通知書");       // 永久標識のみ提出
　　this.dSheetList(vType, "基準点網図");
　　this.dSheetList(vType, "品質評価表");	
　　this.dSheetList(vType, "作業管理写真（測量標写真）");	
　　this.dSheetList(vType, "基準点現況調査報告書");
　　this.dSheetList(vType, "成果数値データ");
　　this.dSheetList(vType, "点検測量簿");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書・検定記録書");     // 高精度（特に永久標識）は必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "水準測量";
　　this.dSheetList(vType, "観測手簿");
　　this.dSheetList(vType, "観測成果表（平均成果表）");
　　this.dSheetList(vType, "水準路線図（平均図）");
　　this.dSheetList(vType, "計算簿");
　　this.dSheetList(vType, "点の記");
　　this.dSheetList(vType, "成果数値データ");
　　this.dSheetList(vType, "建標承諾書");
　　this.dSheetList(vType, "測量標設置位置通知書");       // 新設のみ
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "作業管理写真（測量標写真）");
　　this.dSheetList(vType, "基準点現況調査報告書");
　　this.dSheetList(vType, "点検測量簿");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // ・検定記録書	高精度（特に永久標識）は必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "復旧測量（基準点）";
　　this.dSheetList(vType, "観測手簿");
　　this.dSheetList(vType, "観測記簿");
　　this.dSheetList(vType, "計算簿");
　　this.dSheetList(vType, "平均図（基準点）");
　　this.dSheetList(vType, "成果表");
　　this.dSheetList(vType, "点の記");
　　this.dSheetList(vType, "建標承諾書");                 // 自分の管理地に設置するケース大
　　this.dSheetList(vType, "測量標設置位置通知書");       // 永久標識のみ提出
　　this.dSheetList(vType, "基準点網図");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "作業管理写真（測量標写真）");
　　this.dSheetList(vType, "基準点現況調査報告書");
　　this.dSheetList(vType, "成果数値データ");
　　this.dSheetList(vType, "点検測量簿");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度（特に永久標識）は必要。
　　this.dSheetList(vType, "その他の資料");
　　vType = "復旧測量（水準点）";
　　this.dSheetList(vType, "観測手簿");
　　this.dSheetList(vType, "観測記簿");
　　this.dSheetList(vType, "計算簿");
　　this.dSheetList(vType, "平均図（基準点）");
　　this.dSheetList(vType, "水準路線図（水準点）");
　　this.dSheetList(vType, "成果表");
　　this.dSheetList(vType, "観測成果表（平均成果表）（水準点）");
　　this.dSheetList(vType, "点の記");
　　this.dSheetList(vType, "建標承諾書");                 // 自分の管理地に設置するケース大
　　this.dSheetList(vType, "測量標設置位置通知書");       // 永久標識のみ提出
　　this.dSheetList(vType, "基準点網図");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "作業管理写真（測量標写真）");
　　this.dSheetList(vType, "基準点現況調査報告書");
　　this.dSheetList(vType, "成果数値データ");
　　this.dSheetList(vType, "点検測量簿");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度（特に永久標識）は必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "現地測量";
　　this.dSheetList(vType, "数値地形図データファイル");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "空中写真測量（標定点設置）";
　　this.dSheetList(vType, "標定点成果表");
　　this.dSheetList(vType, "標定点配置図（水準路線図）");
　　this.dSheetList(vType, "標定点測量簿及び同明細簿");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "空中写真測量（対空標識の設置）";
　　this.dSheetList(vType, "対空標識点明細表");
　　this.dSheetList(vType, "偏心計算簿");
　　this.dSheetList(vType, "対空標識点一覧図");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "空中写真測量（撮影（空中写真数値化））";
　　this.dSheetList(vType, "ネガフィルム");
　　this.dSheetList(vType, "数値写真");
　　this.dSheetList(vType, "サムネイル画像");
　　this.dSheetList(vType, "標定図");
　　this.dSheetList(vType, "同時調整成果表（外部標定要素成果表）");
　　this.dSheetList(vType, "撮影記録");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
　　vType = "空中写真測量（刺針）";
　　this.dSheetList(vType, "刺針明細表");
　　this.dSheetList(vType, "偏心計算簿");
　　this.dSheetList(vType, "刺針点一覧図");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "空中写真測量（現地調査）";
　　this.dSheetList(vType, "現地調査結果を整理した空中写真");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "その他の資料");
    vType = "空中写真測量（空中三角測量）";
　　this.dSheetList(vType, "外部標定要素成果表");
　　this.dSheetList(vType, "パスポイント、タイポイント成果表");
　　this.dSheetList(vType, "空中三角測量作業計画、実施一覧図");
　　this.dSheetList(vType, "写真座標測定簿");
　　this.dSheetList(vType, "調整計算簿");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "空中写真測量（数値図化）";
　　this.dSheetList(vType, "数値地形図データファイル（必要な場合）");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
　　vType = "空中写真測量（補測編集）";
　　this.dSheetList(vType, "数値地形図データファイル（必要な場合）");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "既成図数値化（空中三角測量）";
　　this.dSheetList(vType, "数値地形図データファイル");
　　this.dSheetList(vType, "出力図");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
　　vType = "修正測量";
　　this.dSheetList(vType, "数値地形図データファイル");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "写真地図の作成";
　　this.dSheetList(vType, "写真地図データファイル（サンプル出力図）");
　　this.dSheetList(vType, "位置情報ファイル");
　　this.dSheetList(vType, "数値地形モデルファイル");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "航空レーザ測量";
　　this.dSheetList(vType, "数値地形図データファイル（サンプル出力図）");
　　this.dSheetList(vType, "作業記録");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "地図編集";
　　this.dSheetList(vType, "数値地形図データファイル（編集原図データ）");
　　this.dSheetList(vType, "基図データ、編集原図データ等出力図");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "基盤地図情報";
　　this.dSheetList(vType, "基盤地図情報又は基盤地図情報を含む数値地形図データ");
　　this.dSheetList(vType, "品質評価表");
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
　　vType = "路線測量";
　　this.dSheetList(vType, "観測手簿");                   // 条件点の観測、仮BM設置測量、縦断測量、横断測量、詳細測量
　　this.dSheetList(vType, "計算簿");                     // 線形の決定、条件点の観測、IP設置測量、中心線測量、用地幅杭設置測量
　　this.dSheetList(vType, "成果表");                     // 条件点の観測、仮BM設置測量、縦断測量、詳細測量
　　this.dSheetList(vType, "成果数値データ");             // 線形の決定、中心線測量、縦断測量、横断測量、詳細測量
　　this.dSheetList(vType, "引照点図");                   // 中心線測量
　　this.dSheetList(vType, "品質評価表");                 // 仮BM設置測量、縦断測量、横断測量、詳細測量、用地幅杭設置測量
　　this.dSheetList(vType, "メタデータ");
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
　　vType = "河川測量";
　　this.dSheetList(vType, "観測手簿");
　　this.dSheetList(vType, "記録紙");                     // 深浅測量
　　this.dSheetList(vType, "計算簿");                     // 河川測点設置測量、水準基標測量、法線測量、海浜測量、汀線測量
　　this.dSheetList(vType, "成果表");                     // 河川測点設置測量、水準基標測量、縦断測量
　　this.dSheetList(vType, "成果数値データ");             // 縦断測量、横断測量、深浅測量、法線測量、海浜測量、汀線測量
　　this.dSheetList(vType, "点の記");                     // 河川測点設置測量、水準基標測量
　　this.dSheetList(vType, "品質評価表");                 // 河川測点設置測量、水準基標測量、縦断測量、法線測量、海浜測量、汀線測量
　　this.dSheetList(vType, "メタデータ");                 // 河川測点設置測量、水準基標測量、縦断測量、法線測量、海浜測量、汀線測量
　　this.dSheetList(vType, "精度管理表");
　　this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　　this.dSheetList(vType, "その他の資料");
    vType = "用地測量";
　  this.dSheetList(vType, "公図等転写図");               // 資料調査
　  this.dSheetList(vType, "公図等転写連続図");           // 資料調査
　  this.dSheetList(vType, "土地調査表");                 // 資料調査
　  this.dSheetList(vType, "建物の登記記録等調査表");     // 資料調査
　  this.dSheetList(vType, "権利者調査表");               // 資料調査
　  this.dSheetList(vType, "土地境界立会確認書");         // 境界確認
　  this.dSheetList(vType, "観測手簿	境界測量");         // 境界点間測量
　  this.dSheetList(vType, "測量計算簿等");               // 境界測量
　  this.dSheetList(vType, "成果数値データ");             // データファイルの作成
　  this.dSheetList(vType, "面積計算書");                 // 面積計算
　  this.dSheetList(vType, "品質評価表");                 // 境界測量、データファイルの作成
　  this.dSheetList(vType, "メタデータ");                 // 境界測量、データファイルの作成
　  this.dSheetList(vType, "精度管理表");
　  this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　  this.dSheetList(vType, "その他の資料");
    vType = "その他の応用測量";
　  this.dSheetList(vType, "主題図データファイル");
　  this.dSheetList(vType, "品質評価表");
　  this.dSheetList(vType, "メタデータ");
　  this.dSheetList(vType, "精度管理表");
　  this.dSheetList(vType, "検定証明書");                 // 検定記録書	高精度な場合には必要。
　  this.dSheetList(vType, "その他の資料");
　  
    /* ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★*
     * 　　　↑
     * データ入力終了
     *
     * ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★*/
  };
  
  /* コンストラクタ：確認シート
   * arg
   *  string vType  : 作業種別
   *  string vName  : 確認名
   */
  GSI_PublicSurveyData.prototype.dSheetList = function(vType, vName){
    // 作業種別                      確認名
    this.dSheetListType.push(vType); this.dSheetListName.push(vName);
  };
  
  /* -------------------------------------------------------------------------------------------*
   * Class Public
   * -------------------------------------------------------------------------------------------*/
  /* 作業種別
   * return
   *  Array
   */
  GSI_PublicSurveyData.prototype.dWork = function(){
    return this.dWorkType;
  };
  
  /* 確認シート
   * arg
   *  Array  vType  : 条件配列
   * return
   *  Array, Array
   */
  GSI_PublicSurveyData.prototype.dSheet = function(vType){
    var AryName  = new Array();
    
    if(vType != null && vType.length >= 1){
      var n = 0;
      for(n = 0; n < this.dSheetListType.length; n++){
        var i = 0;
        for(i = 0; i < vType.length; i++){
          if(this.dSheetListType[n] == vType[i]){
            AryName.push(this.dSheetListType[n] + "　" + this.dSheetListName[n]);
            break; 
          }
        }
      }
    }

    return { Name : AryName };
  };
  
  // Constractor
  this.Constructor();
};