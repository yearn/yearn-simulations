import subprocess

print("Launcher started...")
vault = "-v 0xA696a63cc78DfFa1a63E9E50587C197387FF6C7E" # vault/strategy/all
strat = "-s 0xB696a63cc78DfFa1a63E9E50587C197387FF6C7E"
#subprocess.call(['./launch_simulator.sh', vault])
subprocess.call(['./launch_simulator.sh', strat])
