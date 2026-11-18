from flask import Flask, request, Response
import yaml
import os
import sys

app = Flask(__name__)

@app.route('/unsafe-run', methods=['GET'])
def unsafe_run():
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