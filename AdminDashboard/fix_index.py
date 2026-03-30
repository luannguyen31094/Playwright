import codecs

modal_html = """  <!-- Tailwind Modal for Product Details -->
  <div id="productDetailModal"
    class="fixed inset-0 hidden items-center justify-center transition-opacity"
    style="z-index: 99999; background-color: rgba(17, 24, 39, 0.75); backdrop-filter: blur(4px);"
    onclick="if(event.target === this) closeProductModal()">
    <div
      class="bg-white dark:bg-[#202938] rounded-2xl w-full max-w-4xl shadow-2xl p-0 overflow-hidden transform transition-all scale-100 flex flex-col max-h-[90vh] mx-4">
      <!-- Modal Header -->
      <div
        class="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 flex justify-between items-center text-white border-b-0">
        <div>
          <h3 class="font-bold text-xl inline-flex items-center gap-2">
            <svg class="w-6 h-6 text-blue-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
            Hồ Sơ Mổ Xẻ Sản Phẩm
          </h3>
          <p class="text-blue-100 text-sm mt-1 font-mono tracking-wide opacity-80"><span id="pModal_id">N/A</span>
          </p>
        </div>
        <button onclick="closeProductModal()"
          class="text-white hover:text-red-300 transition bg-white/10 hover:bg-white/20 rounded-full p-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-6 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-8 text-gray-700 dark:text-gray-300">
        <!-- Cột Trái -->
        <div class="space-y-6">
          <div
            class="relative rounded-xl overflow-hidden shadow border border-gray-200 dark:border-gray-800 aspect-[4/3] flex items-center justify-center bg-gray-100 dark:bg-gray-800 group">
            <img id="pModal_img" src="img/placeholder.jpg"
              class="object-contain w-full h-full transition-transform duration-500 group-hover:scale-105"
              alt="Product Thumbnail">
            <div
              class="absolute top-3 right-3 bg-red-500 text-white font-black px-3 py-1 rounded-full text-sm shadow border border-red-700 uppercase"
              id="pModal_discount">Sale 0%</div>
          </div>

          <div
            class="bg-indigo-50/50 dark:bg-indigo-900/10 p-5 border border-indigo-100 dark:border-indigo-800/30 rounded-xl space-y-4">
            <h4 class="font-bold text-[17px] text-indigo-900 dark:text-indigo-200 line-clamp-3 leading-snug"
              id="pModal_title">Tên Sản Phẩm</h4>

            <div class="grid grid-cols-2 gap-3 mt-4">
              <div
                class="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <div class="text-[11px] text-gray-400 uppercase font-black">💰 Giá Khách Mua</div>
                <div class="text-lg font-black text-rose-600 mt-1 truncate" id="pModal_price">0 VNĐ</div>
              </div>
              <div
                class="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <div class="text-[11px] text-gray-400 uppercase font-black">💸 Tiền Cò (Hoa Hồng)</div>
                <div class="text-lg font-black text-emerald-600 mt-1 truncate" id="pModal_commission">0 VNĐ</div>
              </div>
              <div
                class="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <div class="text-[11px] text-gray-400 uppercase font-black">🔥 Đã Chốt Đơn</div>
                <div class="text-lg font-black text-gray-800 dark:text-gray-100 mt-1 truncate" id="pModal_sold">0
                </div>
              </div>
              <div
                class="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-sm border border-gray-100 dark:border-gray-700">
                <div class="text-[11px] text-gray-400 uppercase font-black">⭐ Rate Người Dùng</div>
                <div class="text-lg font-black text-amber-500 mt-1 truncate" id="pModal_rating">⭐ 0</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Cột Phải -->
        <div class="space-y-6 flex flex-col h-full">
          <div
            class="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden shadow-sm flex flex-col">
            <div
              class="bg-gray-50/80 dark:bg-gray-800/80 px-4 py-3 border-b border-gray-200 dark:border-gray-700 font-bold text-gray-600 dark:text-gray-300 flex items-center gap-2 uppercase text-xs tracking-wider">
              <svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z">
                </path>
              </svg>
              Hệ Thống Phân Tích (AI Brain)
            </div>
            <div class="p-5 flex flex-col gap-5 flex-1 bg-white dark:bg-gray-900">
              <div
                class="flex items-center justify-around bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-lg p-3">
                <div class="text-center">
                  <div class="text-[11px] text-gray-400 font-black uppercase tracking-widest mb-1">Điểm AI Máy Tính</div>
                  <div class="text-5xl font-black text-rose-500" id="pModal_ai_score">0</div>
                </div>
                <div class="w-px h-16 bg-gray-200 dark:bg-gray-700"></div>
                <div class="text-center">
                  <div class="text-[11px] text-gray-400 font-black uppercase tracking-widest mb-1">Tổng Lực Chiến Cơ Bản</div>
                  <div class="text-5xl font-black text-blue-600" id="pModal_total_score">0</div>
                </div>
              </div>

              <div class="flex flex-col flex-1 h-full min-h-[150px]">
                <label
                  class="text-[11px] font-black text-indigo-500 uppercase tracking-widest mb-2 flex items-center gap-1">
                  <i data-feather="terminal" class="w-3 h-3"></i> Tóm Tắt Phân Tích (Logs)
                </label>
                <textarea id="pModal_ai_note"
                  class="w-full border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-[#1a202c] focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none resize-none h-full text-[13px] text-gray-700 dark:text-gray-300 font-mono leading-relaxed"
                  readonly></textarea>
              </div>
            </div>
          </div>

          <div class="border border-green-200 dark:border-green-900 rounded-xl overflow-hidden shadow-sm">
            <div
              class="bg-green-50 dark:bg-green-900/50 px-4 py-3 border-b border-green-200 dark:border-green-800 font-bold text-green-800 dark:text-green-300 flex items-center justify-between">
              <span class="flex items-center gap-2 text-sm uppercase">
                Trạng Thái Quy Trình
              </span>
              <div id="pModal_status"></div>
            </div>
            <div
              class="px-4 py-3 bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 text-xs italic text-center">
              Sản phẩm này hiện đang được khóa ở chế độ <b>Chỉ Xem Chi Tiết Thông Tin</b> để bảo vệ luồng Autmation n8n không bị ngắt quãng.
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>\n
"""

with codecs.open('index.html', 'r', 'utf-8') as f:
    text = f.read()

text = text.replace('<!-- DUAL-PERSONA GLOBAL MODALS -->', modal_html + '  <!-- DUAL-PERSONA GLOBAL MODALS -->')

with codecs.open('index.html', 'w', 'utf-8') as f:
    f.write(text)
print("SUCCESS!")
