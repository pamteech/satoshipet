# RASCUNHO - NÃO enviado pro homebrew-core nem pra nenhum tap. Troque pamteech e os sha256 antes de publicar.
# Uso futuro (tap próprio):  brew tap pamteech/satoshipet && brew install satoshipet
class SatoshiPet < Formula
  include Language::Python::Virtualenv

  desc "Pixel-art crypto pet that floats on your desktop and reacts to the market"
  homepage "https://github.com/pamteech/satoshipet"
  url "https://github.com/pamteech/satoshipet/archive/refs/tags/v1.5.0.tar.gz"
  sha256 "TROCAR_PELO_SHA256_DO_TARBALL_DA_TAG"
  license "MIT"

  depends_on "pillow"
  depends_on "python-tk@3.12"
  depends_on "python@3.12"

  # gere com: brew update-python-resources satoshipet  (requests e dependências)
  resource "requests" do
    url "https://files.pythonhosted.org/packages/source/r/requests/requests-2.32.3.tar.gz"
    sha256 "TROCAR"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/satoshipet --version")
    assert_match "BTC", shell_output("#{bin}/satoshipet --list-skins")
  end
end
