with import <nixpkgs> {};
with pkgs.python3Packages;

buildPythonPackage rec {
  name = "mycalculator";
  src = ./.;
  #dontUnpack = true; 
}
