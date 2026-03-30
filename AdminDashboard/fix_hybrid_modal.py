import codecs, re

safe_modal = """  <!-- Tailwind/Inline Hybrid Modal for Product Details -->
  <div id="productDetailModal"
    class="fixed hidden items-center justify-center transition-opacity duration-300"
    style="z-index: 99999; background-color: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px); position: fixed; inset: 0px; top: 0px; left: 0px; right: 0px; bottom: 0px;"
    onclick="if(event.target === this) closeProductModal()">
    <div class="rounded-2xl w-full mx-4 flex flex-col overflow-hidden transform transition-all scale-100"
         style="max-width: 900px; max-height: 90vh; background-color: #ffffff; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6); border: 1px solid #e2e8f0;">
      
      <!-- Modal Header -->
      <div class="px-6 py-4 flex justify-between items-center border-b" style="background: linear-gradient(to right, #2563eb, #4f46e5); border-bottom-color: #e5e7eb;">
        <div style="display: flex; flex-direction: column;">
          <h3 class="font-bold text-xl inline-flex items-center gap-2 text-white" style="color: #ffffff; margin: 0; display: flex; align-items: center; gap: 0.5rem;">
            <svg class="w-6 h-6" style="width: 24px; height: 24px; color: #dbeafe;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
            Hồ Sơ Mổ Xẻ Sản Phẩm
          </h3>
          <p class="text-sm mt-1 font-mono tracking-wide opacity-80" style="color: #dbeafe; margin: 0; padding-left: 2rem;"><span id="pModal_id">N/A</span></p>
        </div>
        <button onclick="closeProductModal()" class="rounded-full p-2 transition" style="background-color: #ef4444; color: white; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0.5rem 1rem; border-radius: 999px;">
          <span style="margin-right: 5px; font-weight: bold; font-size: 13px;">ĐÓNG LẠI (X)</span>
        </button>
      </div>

      <!-- Modal Body -->
      <div class="p-6 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-8 text-gray-700" style="background-color: #f8fafc; color: #334155;">
        <!-- Cột Trái -->
        <div class="space-y-5" style="display: flex; flex-direction: column; gap: 1.25rem;">
          <div class="flex flex-col sm:flex-row gap-5" style="display: flex; gap: 1.25rem; align-items: stretch;">
            <!-- Ảnh thu nhỏ Cố định 140x140 -->
            <div class="relative shrink-0 rounded-xl overflow-hidden shadow-sm border border-gray-200 flex items-center justify-center group"
                 style="width: 140px; height: 140px; flex-shrink: 0; background-color: #f1f5f9; border-color: #e2e8f0; position: relative;">
              <img id="pModal_img" src="img/placeholder.jpg" class="object-cover w-full h-full transition-transform duration-500 group-hover:scale-110" alt="Product Thumbnail" style="width: 100%; height: 100%; object-fit: cover;">
              <div class="absolute top-2 right-2 text-white font-black px-2 py-0.5 rounded text-[10px] shadow border uppercase"
                   style="background-color: #ef4444; border-color: #b91c1c; position: absolute; top: 0.5rem; right: 0.5rem; font-size: 0.65rem; border-radius: 0.25rem; z-index: 10;" id="pModal_discount" title="Sale Discount">Sale 0%</div>
            </div>

            <div class="p-4 rounded-xl flex-1 shadow-sm flex items-center"
                 style="background-color: #eef2ff; border: 1px solid #c7d2fe; flex: 1; display: flex; align-items: center;">
              <h4 class="font-bold text-[16px] leading-relaxed"
                  style="color: #312e81; margin: 0; font-size: 1rem; line-height: 1.625;" id="pModal_title">Tên Sản Phẩm</h4>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3" style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem;">
            <div class="p-3 rounded-lg shadow-sm border" style="background-color: #ffffff; border-color: #f1f5f9;">
              <div class="uppercase font-black" style="font-size: 0.65rem; color: #94a3b8;">Giá Khách Mua</div>
              <div class="font-black mt-1 truncate" style="font-size: 1.125rem; color: #e11d48;" id="pModal_price">0 VNĐ</div>
            </div>
            <div class="p-3 rounded-lg shadow-sm border" style="background-color: #ffffff; border-color: #f1f5f9;">
              <div class="uppercase font-black" style="font-size: 0.65rem; color: #94a3b8;">Cò (Hoa Hồng)</div>
              <div class="font-black mt-1 truncate" style="font-size: 1.125rem; color: #059669;" id="pModal_commission">0 VNĐ</div>
            </div>
            <div class="p-3 rounded-lg shadow-sm border" style="background-color: #ffffff; border-color: #f1f5f9;">
              <div class="uppercase font-black" style="font-size: 0.65rem; color: #94a3b8;">Đã Chốt Lượt Mua</div>
              <div class="font-black mt-1 truncate" style="font-size: 1.125rem; color: #1e293b;" id="pModal_sold">0</div>
            </div>
            <div class="p-3 rounded-lg shadow-sm border" style="background-color: #ffffff; border-color: #f1f5f9;">
              <div class="uppercase font-black" style="font-size: 0.65rem; color: #94a3b8;">Rating (Đánh giá)</div>
              <div class="font-black mt-1 truncate" style="font-size: 1.125rem; color: #f59e0b;" id="pModal_rating">0</div>
            </div>
          </div>
        </div>

        <!-- Cột Phải -->
        <div class="flex flex-col h-full" style="display: flex; flex-direction: column; gap: 1.5rem; height: 100%;">
          <div class="rounded-xl overflow-hidden shadow-sm border flex flex-col flex-1" style="background-color: #ffffff; border-color: #e2e8f0; flex: 1;">
            <div class="px-4 py-3 border-b font-bold flex items-center gap-2 uppercase tracking-wider"
                 style="background-color: #f8fafc; border-bottom-color: #e2e8f0; color: #475569; font-size: 0.75rem; display: flex; align-items: center; gap: 0.5rem;">
              <svg class="w-5 h-5" style="width: 20px; height: 20px; color: #6366f1;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path>
              </svg>
              Hệ Thống Phân Tích (AI Brain)
            </div>
            <div class="p-5 flex flex-col flex-1" style="display: flex; flex-direction: column; gap: 1.25rem;">
              <div class="flex items-center justify-around rounded-lg p-4 shadow-inner border"
                   style="background-color: #f8fafc; border-color: #f1f5f9; box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06); display: flex;">
                <div class="text-center w-1/2" style="width: 50%; text-align: center;">
                  <div class="font-black uppercase tracking-widest mb-2" style="font-size: 0.7rem; color: #94a3b8; margin-bottom: 0.5rem;">Điểm AI Máy Tính</div>
                  <div class="font-black" style="font-size: 3rem; color: #f43f5e; line-height: 1;" id="pModal_ai_score">0</div>
                </div>
                <div style="width: 1px; height: 64px; background-color: #e2e8f0; margin: 0 0.5rem;"></div>
                <div class="text-center w-1/2" style="width: 50%; text-align: center;">
                  <div class="font-black uppercase tracking-widest mb-2" style="font-size: 0.7rem; color: #94a3b8; margin-bottom: 0.5rem;">Lực Chiến Cơ Bản</div>
                  <div class="font-black" style="font-size: 3rem; color: #2563eb; line-height: 1;" id="pModal_total_score">0</div>
                </div>
              </div>

              <div class="flex flex-col flex-1 h-full" style="display: flex; flex-direction: column; min-height: 150px;">
                <label class="font-black uppercase tracking-widest mb-2 flex items-center gap-1" style="font-size: 0.7rem; color: #6366f1; margin-bottom: 0.5rem;">
                  Tóm Tắt Phân Tích (Logs)
                </label>
                <textarea id="pModal_ai_note" class="w-full rounded-lg p-4 outline-none resize-none h-full shadow-inner border"
                  style="background-color: #f8fafc; border-color: #e2e8f0; font-family: monospace; font-size: 0.8125rem; color: #334155; line-height: 1.625; min-height: 150px; flex: 1; width: 100%; border-radius: 0.5rem;"
                  readonly></textarea>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="px-6 py-4 flex justify-end border-t" style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end;">
          <button type="button" onclick="closeProductModal()" class="px-5 py-2 rounded-lg font-medium transition shadow-sm"
                  style="background-color: #94a3b8; color: #ffffff; border: none; cursor: pointer; padding: 0.5rem 1.5rem; font-weight: bold;">ĐÓNG CỬA SỔ</button>
      </div>
    </div>
  </div>\n"""

with codecs.open('index.html', 'r', 'utf-8') as f:
    text = f.read()

text = re.sub(r'(<!-- Tailwind Modal for Product Details -->|  <!-- Tailwind/Inline Hybrid Modal for Product Details -->)[\s\S]*?(?=<!-- DUAL-PERSONA GLOBAL MODALS -->)', safe_modal, text)

with codecs.open('index.html', 'w', 'utf-8') as f:
    f.write(text)
print("Hybrid Inline Modal Inject Successful")
