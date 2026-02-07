/*
 * Dual MUX Controller for Ion Gel Touch Position Estimation
 * 
 * このファームウェアは、2つのCD4051マルチプレクサを独立制御します。
 * - Mux1 (Source側): D2, D3, D4 で制御
 * - Mux2 (Sink側): D5, D6, D7 で制御
 * 
 * シリアル通信プロトコル:
 *   コマンド: "S<source_ch>K<sink_ch>\n"
 *   例: "S0K1\n" → Source Ch0, Sink Ch1 を選択
 *   応答: "OK:S0K1\n"
 */

// ========================================
// ピン定義
// ========================================

// Mux1 (Source側) 制御ピン
const int MUX1_S0 = 2;  // D2
const int MUX1_S1 = 3;  // D3
const int MUX1_S2 = 4;  // D4

// Mux2 (Sink側) 制御ピン
const int MUX2_S0 = 5;  // D5
const int MUX2_S1 = 6;  // D6
const int MUX2_S2 = 7;  // D7

// ========================================
// グローバル変数
// ========================================

int currentSourceCh = 0;  // 現在のSourceチャンネル
int currentSinkCh = 1;    // 現在のSinkチャンネル

// ========================================
// 初期化
// ========================================

void setup() {
  // シリアル通信初期化
  Serial.begin(9600);
  
  // Mux1制御ピンを出力に設定
  pinMode(MUX1_S0, OUTPUT);
  pinMode(MUX1_S1, OUTPUT);
  pinMode(MUX1_S2, OUTPUT);
  
  // Mux2制御ピンを出力に設定
  pinMode(MUX2_S0, OUTPUT);
  pinMode(MUX2_S1, OUTPUT);
  pinMode(MUX2_S2, OUTPUT);
  
  // 初期状態: Source Ch0, Sink Ch1
  setMuxChannels(0, 1);
  
  // 起動メッセージ
  Serial.println("Dual MUX Controller Ready");
  Serial.println("Command format: S<source_ch>K<sink_ch>");
}

// ========================================
// メインループ
// ========================================

void loop() {
  // シリアルデータ受信待ち
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();  // 前後の空白を削除
    
    // コマンド解析
    if (parseCommand(command)) {
      // 成功応答
      Serial.print("OK:");
      Serial.println(command);
    } else {
      // エラー応答
      Serial.print("ERROR:");
      Serial.println(command);
    }
  }
}

// ========================================
// コマンド解析
// ========================================

bool parseCommand(String cmd) {
  /*
   * コマンド形式: "S<source_ch>K<sink_ch>"
   * 例: "S0K1" → Source Ch0, Sink Ch1
   * 
   * 戻り値: 解析成功時true、失敗時false
   */
  
  // 最小長チェック (例: "S0K1" = 4文字)
  if (cmd.length() < 4) {
    return false;
  }
  
  // 'S' で始まるかチェック
  if (cmd.charAt(0) != 'S') {
    return false;
  }
  
  // 'K' の位置を探す
  int kPos = cmd.indexOf('K');
  if (kPos == -1) {
    return false;
  }
  
  // Source チャンネルを抽出
  String sourceStr = cmd.substring(1, kPos);
  int sourceCh = sourceStr.toInt();
  
  // Sink チャンネルを抽出
  String sinkStr = cmd.substring(kPos + 1);
  int sinkCh = sinkStr.toInt();
  
  // 範囲チェック (0-7)
  if (sourceCh < 0 || sourceCh > 7 || sinkCh < 0 || sinkCh > 7) {
    return false;
  }
  
  // 同じチャンネルは選択不可
  if (sourceCh == sinkCh) {
    return false;
  }
  
  // Muxチャンネルを設定
  setMuxChannels(sourceCh, sinkCh);
  
  return true;
}

// ========================================
// Muxチャンネル設定
// ========================================

void setMuxChannels(int sourceCh, int sinkCh) {
  /*
   * 2つのMuxのチャンネルを独立して設定
   * 
   * 引数:
   *   sourceCh: Source側チャンネル (0-7)
   *   sinkCh: Sink側チャンネル (0-7)
   */
  
  // Mux1 (Source側) を設定
  setMux1(sourceCh);
  
  // Mux2 (Sink側) を設定
  setMux2(sinkCh);
  
  // 現在の設定を保存
  currentSourceCh = sourceCh;
  currentSinkCh = sinkCh;
}

// ========================================
// Mux1 (Source側) 設定
// ========================================

void setMux1(int channel) {
  /*
   * Mux1のチャンネルを設定
   * 
   * チャンネル選択は3ビットのバイナリ値で行う:
   *   Ch0 = 000, Ch1 = 001, Ch2 = 010, ..., Ch7 = 111
   */
  
  // S0 (LSB)
  digitalWrite(MUX1_S0, (channel & 0x01) ? HIGH : LOW);
  
  // S1
  digitalWrite(MUX1_S1, (channel & 0x02) ? HIGH : LOW);
  
  // S2 (MSB)
  digitalWrite(MUX1_S2, (channel & 0x04) ? HIGH : LOW);
}

// ========================================
// Mux2 (Sink側) 設定
// ========================================

void setMux2(int channel) {
  /*
   * Mux2のチャンネルを設定
   * 
   * チャンネル選択は3ビットのバイナリ値で行う:
   *   Ch0 = 000, Ch1 = 001, Ch2 = 010, ..., Ch7 = 111
   */
  
  // S0 (LSB)
  digitalWrite(MUX2_S0, (channel & 0x01) ? HIGH : LOW);
  
  // S1
  digitalWrite(MUX2_S1, (channel & 0x02) ? HIGH : LOW);
  
  // S2 (MSB)
  digitalWrite(MUX2_S2, (channel & 0x04) ? HIGH : LOW);
}
