from flask import Flask, request, Response
import yaml
import os
import sys

app = Flask(__name__)

@app.route('/unsafe-run', methods=['GET', 'POST'])
def unsafe_run():
    # Handle POST request: receive results posted back from the client script
    if request.method == 'POST':
        try:
            # Parse incoming JSON or YAML data
            data = request.get_json(silent=True)
            if not data:
                data = yaml.safe_load(request.data)
            
            print("[+] Successfully received demo results from client:")
            print(yaml.dump(data, sort_keys=False))

            response_data = {
                "status": "RESULTS_RECEIVED",
                "received_keys": list(data.keys()) if isinstance(data, dict) else []
            }
            return Response(yaml.dump(response_data), mimetype='text/yaml')

        except Exception as e:
            error_data = {"error": str(e)}
            return Response(yaml.dump(error_data), mimetype='text/yaml', status=500)

    # Handle GET request: original RCE execution demo
    code_str = request.args.get('code', '')
    if not code_str:
        return "input param ?code=...", 400

    try:
        if not code_str.startswith("__import__") and not code_str.startswith("os"):
            full_code = f"__import__('os').popen('{code_str}').read()"
        else:
            full_code = code_str

        command_output = eval(full_code)

        response_data = {
            "status": "UNSAFE_RCE_SUCCESS",
            "executed_command": code_str,
            "output": command_output
        }
        yaml_output = yaml.dump(response_data)
        
        return Response(yaml_output, mimetype='text/yaml')

    except Exception as e:
        error_data = {"error": str(e)}
        return Response(yaml.dump(error_data), mimetype='text/yaml', status=500)

if __name__ == '__main__':
    print("[*] Server running at http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True)